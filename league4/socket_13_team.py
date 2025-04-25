import socket
import json
import sys
import math
import random
import time

class GameClient:
    def __init__(self, port, player_id, player_num):
        self.port = port
        self.player_id = player_id
        self.player_num = player_num
        self.sock = None
    
    def connect(self):
        """Connect to the game server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(('localhost', self.port))
            print(f"Connected to game server on port {self.port}")
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def run(self):
        """Main loop to receive game state and send moves"""
        try:
            while True:
                # Receive game state
                game_state_str = self.receive_message()
                if not game_state_str:
                    break
                
                try:
                    # Parse JSON game state
                    game_state = json.loads(game_state_str)
                    # Make move based on game state
                    move = self.make_move(game_state)
                    # Send move back to server
                    move_str = json.dumps(move)
                    self.send_message(move_str + '\n')
                except json.JSONDecodeError as e:
                    print(f"JSON error: {e}")
                    break
        except Exception as e:
            print(f"Error in run loop: {e}")
        finally:
            self.close()
    
    def receive_message(self):
        """Receive a complete message from the server"""
        result = ""
        while True:
            chunk = self.sock.recv(4096).decode('utf-8')
            if not chunk:
                return ""
            
            result += chunk
            if '\n' in chunk:
                break
        
        return result
    
    def send_message(self, message):
        """Send a message to the server"""
        try:
            self.sock.sendall(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def close(self):
        """Close the connection"""
        if self.sock:
            self.sock.close()
            self.sock = None
    
    def make_move(self, game_state):
        """
        Enhanced strategy for Mushroom Wars
        """
        player = game_state["player"]
        size = game_state["size"]
        bases = game_state["bases"]
        movements = game_state["movements"]
        game_time = game_state["game_time"]
        
        # Categorize bases
        my_bases = [b for b in bases if b["owner"] == player]
        enemy_bases = [b for b in bases if b["owner"] not in (0, player)]
        neutral_bases = [b for b in bases if b["owner"] == 0]
        
        # Calculate distances between all bases
        def distance(base1, base2):
            return math.sqrt((base1["x"] - base2["x"])**2 + (base1["y"] - base2["y"])**2)
        
        # Helper functions to identify special base types
        def is_speedy_base(base):
            return base.get("type", "") == "SpeedyBase"
        
        def is_special_base(base):
            return base.get("type", "") == "SpecialBase"
        
        # Strategy 0: Very early game aggressive opening (first 3 seconds)
        if game_time < 3:
            moves = self.early_aggressive_move(my_bases, enemy_bases, distance)
            if moves:
                return {"moves": moves}
        
        # Strategy 1: Early game expansion (first 12 seconds)
        elif game_time < 10:
            moves = self.early_game_strategy(my_bases, neutral_bases, enemy_bases, distance, is_speedy_base, is_special_base)
            if moves:
                return {"moves": moves}
        
        # Strategy 2: Mid-game consolidation
        elif game_time < 25:
            moves = self.mid_game_strategy(my_bases, neutral_bases, enemy_bases, distance, is_speedy_base, is_special_base)
            if moves:
                return {"moves": moves}
        
        # Strategy 3: Late game domination
        else:
            moves = self.late_game_strategy(my_bases, enemy_bases, neutral_bases, distance, is_speedy_base, is_special_base, 
                                        game_time, game_state["game_max_duration"])
            if moves:
                return {"moves": moves}
        
        # Default: Defensive stance if no moves found
        return {"moves": []}

    def early_aggressive_move(self, my_bases, enemy_bases, distance_func):
        """
        Aggressive opening move to capture an enemy base right at the start
        """
        moves = []
        
        # Find strongest base to launch attack from
        strongest_base = None
        for base in my_bases:
            if not strongest_base or base["units"] > strongest_base["units"]:
                strongest_base = base
        
        if not strongest_base or strongest_base["units"] < 20:
            return []  # Not enough units for aggressive opening
            
        # Find closest enemy base
        if enemy_bases:
            target = min(enemy_bases, key=lambda b: distance_func(strongest_base, b))
            
            # Send a strong 15-unit force to capture it
            if strongest_base["units"] - 15 >= 5:  # Keep some defense
                moves.append([
                    strongest_base["x"], strongest_base["y"],
                    target["x"], target["y"],
                    10  # Fixed aggressive force
                ])
                
        return moves

    def early_game_strategy(self, my_bases, neutral_bases, enemy_bases, distance_func, is_speedy_base, is_special_base):
        """
        Focus on capturing neutral bases with optimal force and prioritization,
        with higher priority for special base types and mid-range distances
        """
        moves = []
        
        # Identify special neutral bases to prioritize
        neutral_speedy_bases = [b for b in neutral_bases if is_speedy_base(b)]
        neutral_special_bases = [b for b in neutral_bases if is_special_base(b)]
        regular_neutral_bases = [b for b in neutral_bases 
                              if not is_speedy_base(b) and not is_special_base(b)]
        
        # Find any speedy bases we own
        my_speedy_bases = [base for base in my_bases if is_speedy_base(base)]
        
        # Calculate distance ranges for all neutral bases
        base_distances = {}
        max_distance = 0
        
        for my_base in my_bases:
            for neutral in neutral_bases:
                dist = distance_func(my_base, neutral)
                base_key = (my_base["x"], my_base["y"], neutral["x"], neutral["y"])
                base_distances[base_key] = dist
                max_distance = max(max_distance, dist)
        
        # Define what mid-range means (between 40% and 70% of max distance)
        mid_range_min = max_distance * 0.4
        mid_range_max = max_distance * 0.7
        
        # First use speedy bases if we have them and they have enough units
        if my_speedy_bases:
            speedy_with_units = [base for base in my_speedy_bases if base["units"] > 15]
            
            for my_base in sorted(speedy_with_units, key=lambda b: -b["units"]):
                # First try to capture special/speedy neutral bases
                priority_targets = neutral_speedy_bases + neutral_special_bases
                
                if priority_targets:
                    # Score based on both unit count and mid-range preference
                    targets = []
                    for target in priority_targets:
                        dist = distance_func(my_base, target)
                        # Lower score is better - add penalty for bases outside mid-range
                        mid_range_score = 0
                        if dist < mid_range_min:
                            mid_range_score = (mid_range_min - dist) * 3  # Penalty for too close
                        elif dist > mid_range_max:
                            mid_range_score = (dist - mid_range_max) * 2  # Smaller penalty for too far
                        
                        score = target["units"] * 1.5 + mid_range_score
                        targets.append((target, score))
                    
                    targets.sort(key=lambda x: x[1])  # Sort by score
                    
                    for target, _ in targets:
                        required_units = target["units"] + 5  # Extra buffer for important bases
                        if my_base["units"] - required_units > 10:  # Keep stronger defense
                            moves.append([
                                my_base["x"], my_base["y"],
                                target["x"], target["y"],
                                required_units
                            ])
                            my_base["units"] -= required_units
                            if target in neutral_speedy_bases:
                                neutral_speedy_bases.remove(target)
                            if target in neutral_special_bases:
                                neutral_special_bases.remove(target)
                            break
        
        # Then use regular bases to capture remaining neutral bases
        for my_base in sorted(my_bases, key=lambda b: -b["units"]):
            if my_base["units"] <= 10:  # Maintain defensive buffer
                continue
            
            # First prioritize any remaining special/speedy bases
            priority_targets = neutral_speedy_bases + neutral_special_bases
            
            if priority_targets:
                # Prefer mid-range special bases
                targets = []
                for target in priority_targets:
                    dist = distance_func(my_base, target)
                    # Calculate mid-range preference score
                    mid_range_score = 0
                    if dist < mid_range_min:
                        mid_range_score = (mid_range_min - dist) * 3  # Penalty for too close
                    elif dist > mid_range_max:
                        mid_range_score = (dist - mid_range_max) * 2  # Smaller penalty for too far
                    
                    score = target["units"] * 1.5 + mid_range_score
                    targets.append((target, score))
                
                targets.sort(key=lambda x: x[1])  # Sort by score
                
                for target, _ in targets:
                    required_units = target["units"] + 5  # Extra buffer for important bases
                    if my_base["units"] - required_units > 5:
                        moves.append([
                            my_base["x"], my_base["y"],
                            target["x"], target["y"],
                            required_units
                        ])
                        my_base["units"] -= required_units
                        if target in neutral_speedy_bases:
                            neutral_speedy_bases.remove(target)
                        if target in neutral_special_bases:
                            neutral_special_bases.remove(target)
                        break
            
            # Then go for regular bases if we couldn't get special ones, preferring mid-range
            if my_base["units"] > 15 and regular_neutral_bases:
                targets = []
                for target in regular_neutral_bases:
                    dist = distance_func(my_base, target)
                    # Calculate mid-range preference score
                    mid_range_score = 0
                    if dist < mid_range_min:
                        mid_range_score = (mid_range_min - dist) * 3  # Penalty for too close
                    elif dist > mid_range_max:
                        mid_range_score = (dist - mid_range_max) * 2  # Smaller penalty for too far
                    
                    score = target["units"] * 2 + mid_range_score
                    targets.append((target, score))
                
                targets.sort(key=lambda x: x[1])  # Sort by score
                
                for target, _ in targets:
                    required_units = target["units"] + 3
                    if my_base["units"] - required_units > 5:
                        moves.append([
                            my_base["x"], my_base["y"],
                            target["x"], target["y"],
                            required_units
                        ])
                        my_base["units"] -= required_units
                        regular_neutral_bases.remove(target)
                        break
        
        return moves

    def mid_game_strategy(self, my_bases, neutral_bases, enemy_bases, distance_func, is_speedy_base, is_special_base):
        """
        Balance between expansion and preparing for attacks with prioritization based on base types
        """
        moves = []
        
        # Identify special bases
        enemy_speedy_bases = [b for b in enemy_bases if is_speedy_base(b)]
        enemy_special_bases = [b for b in enemy_bases if is_special_base(b)]
        neutral_speedy_bases = [b for b in neutral_bases if is_speedy_base(b)]
        neutral_special_bases = [b for b in neutral_bases if is_special_base(b)]
        
        # Find any speedy bases we own
        my_speedy_bases = [base for base in my_bases if is_speedy_base(base)]
        
        # Calculate threat levels for each base
        base_threats = {}
        for my_base in my_bases:
            threat_level = 0
            base_key = (my_base["x"], my_base["y"])
            for enemy_base in enemy_bases:
                dist = distance_func(my_base, enemy_base)
                if dist < 4:  # Only consider nearby threats
                    threat_mult = 1.5
                    if is_speedy_base(enemy_base):
                        threat_mult = 2.0  # Speedy bases are more threatening
                    threat_level += enemy_base["units"] / (dist * threat_mult)
            base_threats[base_key] = threat_level
        
        # 1. First priority: Capture neutral speedy/special bases
        if neutral_speedy_bases or neutral_special_bases:
            priority_targets = neutral_speedy_bases + neutral_special_bases
            
            # Prefer using speedy bases for this if we have them
            available_bases = my_speedy_bases if my_speedy_bases else my_bases
            
            for my_base in sorted(available_bases, key=lambda b: -b["units"]):
                if my_base["units"] <= 15:  # Need sufficient forces
                    continue
                
                targets = sorted(priority_targets, 
                            key=lambda b: (b["units"] * 1.5 + distance_func(my_base, b)))
                
                for target in targets:
                    required_units = target["units"] + 7  # Ensure capture of important base
                    if my_base["units"] - required_units > 8:
                        moves.append([
                            my_base["x"], my_base["y"],
                            target["x"], target["y"],
                            required_units
                        ])
                        my_base["units"] -= required_units
                        if target in priority_targets:
                            priority_targets.remove(target)
                        break
        
        # 2. Second priority: Attack enemy speedy/special bases
        if enemy_speedy_bases or enemy_special_bases:
            priority_targets = enemy_speedy_bases + enemy_special_bases
            
            for my_base in sorted(my_bases, key=lambda b: -b["units"]):
                if my_base["units"] <= 20:  # Need stronger forces for enemy special bases
                    continue
                
                targets = sorted(priority_targets, 
                            key=lambda b: (b["units"] * 2 + distance_func(my_base, b)))
                
                for target in targets:
                    required_units = target["units"] + 10  # Need significant buffer
                    if my_base["units"] - required_units > 10:
                        moves.append([
                            my_base["x"], my_base["y"],
                            target["x"], target["y"],
                            required_units
                        ])
                        my_base["units"] -= required_units
                        break
        
        # 3. Defend vulnerable bases, especially special ones
        vulnerable_bases = []
        for base in my_bases:
            base_key = (base["x"], base["y"])
            threat = base_threats.get(base_key, 0)
            priority = 1
            if is_speedy_base(base):
                priority = 0  # Higher priority (lower number)
            elif is_special_base(base):
                priority = 0  # Higher priority (lower number)
            
            if base["units"] < 10 or threat > 15:
                vulnerable_bases.append((base, priority, threat))
        
        # Sort by priority (special bases first), then by threat level
        vulnerable_bases.sort(key=lambda x: (x[1], -x[2]))
        
        # Send reinforcements to vulnerable bases
        strong_bases = [b for b in my_bases if b["units"] > 20]
        
        for weak_base, _, threat in vulnerable_bases:
            for strong_base in sorted(strong_bases, key=lambda b: distance_func(b, weak_base)):
                # Skip if this is the same base
                if (strong_base["x"], strong_base["y"]) == (weak_base["x"], weak_base["y"]):
                    continue
                    
                if strong_base["units"] > 25:
                    # More reinforcements for special bases or high threats
                    defense_buffer = 10
                    if is_speedy_base(weak_base) or is_special_base(weak_base):
                        defense_buffer = 15
                    
                    reinforce_units = max(10, min(int(threat), 20))
                    if strong_base["units"] - reinforce_units > 10:
                        moves.append([
                            strong_base["x"], strong_base["y"],
                            weak_base["x"], weak_base["y"],
                            reinforce_units
                        ])
                        strong_base["units"] -= reinforce_units
                        break
        
        # 4. Target regular enemy bases
        regular_enemy_bases = [b for b in enemy_bases 
                           if not is_speedy_base(b) and not is_special_base(b)]
        
        if regular_enemy_bases:
            for my_base in sorted(my_bases, key=lambda b: -b["units"]):
                if my_base["units"] <= 15:
                    continue
                
                # Calculate priority score for enemy bases
                targets = sorted(regular_enemy_bases, 
                            key=lambda b: (b["units"] * 3 + distance_func(my_base, b)))
                
                for target in targets:
                    required_units = target["units"] + 5
                    if my_base["units"] - required_units > 5:
                        moves.append([
                            my_base["x"], my_base["y"],
                            target["x"], target["y"],
                            required_units
                        ])
                        my_base["units"] -= required_units
                        break
        
        # 5. Capture regular neutral bases
        regular_neutral_bases = [b for b in neutral_bases 
                              if not is_speedy_base(b) and not is_special_base(b)]
        
        if regular_neutral_bases:
            for my_base in sorted(my_bases, key=lambda b: -b["units"]):
                if my_base["units"] <= 10:
                    continue
                
                targets = sorted(regular_neutral_bases, 
                            key=lambda b: (b["units"] * 2 + distance_func(my_base, b)))
                
                for target in targets:
                    required_units = target["units"] + 5
                    if my_base["units"] - required_units > 5:
                        moves.append([
                            my_base["x"], my_base["y"],
                            target["x"], target["y"],
                            required_units
                        ])
                        my_base["units"] -= required_units
                        regular_neutral_bases.remove(target)
                        break

        return moves

    def late_game_strategy(self, my_bases, enemy_bases, neutral_bases, distance_func, is_speedy_base, is_special_base, current_time, max_duration):
        """
        Final push to eliminate enemy or maximize unit count
        """
        moves = []
        time_left = max_duration - current_time
        
        # Identify special bases
        enemy_speedy_bases = [b for b in enemy_bases if is_speedy_base(b)]
        enemy_special_bases = [b for b in enemy_bases if is_special_base(b)]
        neutral_special_bases = [b for b in neutral_bases if is_special_base(b) or is_speedy_base(b)]
        
        # If time is running out, focus on capturing/eliminating special bases first
        # as they can change the unit count dramatically at the end
        if time_left < 40 and (enemy_speedy_bases or enemy_special_bases):
            priority_targets = enemy_speedy_bases + enemy_special_bases
            
            for target in sorted(priority_targets, key=lambda b: b["units"]):
                # Find all nearby bases that can contribute to attack
                contributors = sorted(
                    [b for b in my_bases if b["units"] > 15],
                    key=lambda b: distance_func(b, target))
                
                total_sent = 0
                needed = target["units"] + 15  # Attack with buffer
                
                for base in contributors[:3]:  # Limit to 3 bases for this attack
                    if total_sent >= needed:
                        break
                    
                    available = min(base["units"] - 5, needed - total_sent)
                    if available > 0:
                        moves.append([
                            base["x"], base["y"],
                            target["x"], target["y"],
                            available
                        ])
                        total_sent += available
                        base["units"] -= available
        
        # If we're clearly winning, go for elimination
        elif len(my_bases) > 2 * len(enemy_bases):
            # First target special enemy bases
            priority_targets = enemy_speedy_bases + enemy_special_bases
            regular_enemies = [b for b in enemy_bases if b not in priority_targets]
            
            # Attack priority targets first
            for target in sorted(priority_targets, key=lambda b: b["units"]):
                contributors = sorted(
                    [b for b in my_bases if b["units"] > 15],
                    key=lambda b: distance_func(b, target))
                
                total_sent = 0
                needed = target["units"] + 15
                
                for base in contributors[:3]:
                    if total_sent >= needed:
                        break
                    
                    available = min(base["units"] - 5, needed - total_sent)
                    if available > 0:
                        moves.append([
                            base["x"], base["y"],
                            target["x"], target["y"],
                            available
                        ])
                        total_sent += available
                        base["units"] -= available
            
            # Then attack regular enemy bases
            for target in sorted(regular_enemies, key=lambda b: b["units"]):
                contributors = sorted(
                    [b for b in my_bases if b["units"] > 15],
                    key=lambda b: distance_func(b, target))
                
                total_sent = 0
                needed = target["units"] + 15
                
                for base in contributors[:2]:  # Limit to 2 bases for regular targets
                    if total_sent >= needed:
                        break
                    
                    available = min(base["units"] - 5, needed - total_sent)
                    if available > 0:
                        moves.append([
                            base["x"], base["y"],
                            target["x"], target["y"],
                            available
                        ])
                        total_sent += available
                        base["units"] -= available
        
        # If time is very short, maximize unit count by consolidating to special bases if possible
        elif time_left < 20:
            my_special_bases = [b for b in my_bases if is_special_base(b) or is_speedy_base(b)]
            
            # If we have special bases, consolidate to them
            if my_special_bases:
                target_base = max(my_special_bases, key=lambda b: b["units"])
                
                for base in [b for b in my_bases if b != target_base and b["units"] > 5]:
                    send_units = base["units"] - 3  # Leave minimal defense
                    moves.append([
                        base["x"], base["y"],
                        target_base["x"], target_base["y"],
                        send_units
                    ])
            # Otherwise consolidate to strongest base
            else:
                strongest_base = max(my_bases, key=lambda b: b["units"])
                
                for base in [b for b in my_bases if b != strongest_base and b["units"] > 5]:
                    send_units = base["units"] - 5
                    moves.append([
                        base["x"], base["y"],
                        strongest_base["x"], strongest_base["y"],
                        send_units
                    ])
        
        # Default to mid-game strategy if none of the above apply
        else:
            moves = self.mid_game_strategy(my_bases, neutral_bases, enemy_bases, distance_func, 
                                        is_speedy_base, is_special_base)
        
        return moves

def main():
    print("🚨 Python Player script is running", flush=True)
    if len(sys.argv) < 4:
        print("Usage: python socket_player_template.py <port> <player_id> <player_num>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    player_id = sys.argv[2]
    player_num = int(sys.argv[3])
    
    client = GameClient(port, player_id, player_num)
    
    if not client.connect():
        sys.exit(1)
    
    client.run()

if __name__ == "__main__":
    main()
