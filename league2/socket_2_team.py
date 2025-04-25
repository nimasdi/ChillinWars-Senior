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
        self.enemy_base_states = []
        self.base_unit_histories = {}
        self.neutral_camp_unit_histories = {}

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
            
        
    def opposite(self):
        if self.player_num == 1:
            return 2
        else:
            return 1
        
    
    def get_enemy_soldiers(self,game_state, player_num):
        
        enemy_player = 2 if player_num == 1 else 1
        movements = game_state.get("movements", [])
        
        enemy_moving_units = sum(move["units"] for move in movements if move["owner"] == enemy_player)
        
        return enemy_moving_units
    
    
    def get_slope_for_base_changes(self):
        slopes = {}
        for key, history in self.base_unit_histories.items():
            if len(history) >= 2:
                y2, y1 = history[-1], history[-2]
                slope = y2 - y1
                slopes[key] = slope
            else:
                slopes[key] = 0 
        return slopes
    
    def estimate_attack_probability(self, target_base, game_state, player_num):
        base_key = (target_base["x"], target_base["y"])
        slope = 0

        if base_key in self.base_unit_histories and len(self.base_unit_histories[base_key]) >= 2:
            y2, y1 = self.base_unit_histories[base_key][-1], self.base_unit_histories[base_key][-2]
            slope = y2 - y1

        slope_component = max(0, -slope / 5.0)

        enemy_player = 2 if player_num == 1 else 1
        movements = game_state.get("movements", [])
        directional_threat = 0.0

        for move in movements:
            if move["owner"] == enemy_player:
                dx = target_base["x"] - move["current_x"]
                dy = target_base["y"] - move["current_y"]
                dist = math.sqrt(dx**2 + dy**2)

                if dist < 5:
                    # Approximate movement vector from source to current
                    mv_dx = move["current_x"] - move["source_x"]
                    mv_dy = move["current_y"] - move["source_y"]
                    mv_mag = math.sqrt(mv_dx**2 + mv_dy**2)

                    if mv_mag > 0:
                        # Normalize vectors
                        norm_mv_dx = mv_dx / mv_mag
                        norm_mv_dy = mv_dy / mv_mag

                        dir_mag = math.sqrt(dx**2 + dy**2)
                        dir_dx = dx / dir_mag
                        dir_dy = dy / dir_mag

                        # Cosine similarity
                        alignment = norm_mv_dx * dir_dx + norm_mv_dy * dir_dy
                        alignment = max(0, alignment)  # Only consider moving toward base

                        alignment_boost = 1.0 + 2.0 * alignment  # Up to 3x boost
                    else:
                        alignment_boost = 1.0  # Stationary

                    directional_threat += (move["units"] * alignment_boost) / (dist + 0.1)

        directional_threat = min(directional_threat / 50.0, 1.0)

        # Proximity threat from enemy bases
        enemy_bases = [b for b in game_state["bases"] if b["owner"] == enemy_player]
        proximity_threat = 0.0
        for enemy_base in enemy_bases:
            dist = math.sqrt((target_base["x"] - enemy_base["x"])**2 + (target_base["y"] - enemy_base["y"])**2)
            if dist < 6:
                proximity_threat += enemy_base["units"] / (dist + 0.1)

        proximity_threat = min(proximity_threat / 100.0, 1.0)

        probability = 0.4 * slope_component + 0.3 * directional_threat + 0.3 * proximity_threat
        return min(probability, 1.0)
    
    def select_mode(self, game_state, player_num):
        """Selects mode based on the enemy's state, with weight adjustments for units and bases."""
        player = player_num
        
        # Extract bases and movements from JSON
        bases = game_state["bases"]
        moves = game_state["movements"]  # assuming moves is a list of moves in the game state
        
        # Calculate the total number of units for the enemy
        enemy_player = 2 if player == 1 else 1
        my_bases = [b for b in bases if b["owner"] == player]
        
        enemy_bases = [b for b in bases if b["owner"] == enemy_player]
        enemy_units_in_bases = sum(base["units"] for base in enemy_bases)
        
        # Calculate the total number of enemy units on the move
        enemy_units_on_move = 0
        for move in moves:
            if move["owner"] == enemy_player:
                enemy_units_on_move += move["units"]
        
        my_units_in_base = sum(base["units"] for base in my_bases)
        
        total_enemy_units = enemy_units_in_bases + enemy_units_on_move
        
        # Count the number of bases
        enemy_bases_count = len(enemy_bases)
        my_bases_count = len(my_bases)
        
        # Calculate the weight for bases
        base_weight = my_bases_count / (my_bases_count + enemy_bases_count)  # weight based on base count
        
        # Calculate the weight for enemy's total units
        unit_diff = total_enemy_units - my_units_in_base
        unit_weight = 0
        if unit_diff < -15:  # If we have at least 15 more units than the enemy
            unit_weight = 0.7  # Give more weight to attacking
        
        # Combine weights for both base count and units
        attack_weight = unit_weight + base_weight
        extend_weight = 1 - attack_weight  # The remainder goes to extending mode
        
        # Decide mode based on weighted chance
        mode_decision = random.choices(
            ["attack", "extend"], 
            weights=[attack_weight, extend_weight], 
            k=1
        )[0]
        
        return mode_decision, total_enemy_units
    
    
    def make_move(self, game_state):
        """
        Implement a strategy with three modes: Attack, Defend, and Extend.
        - Attack: Focuses on attacking weak enemy or neutral bases.
        - Defend: Focuses on reinforcing bases under threat.
        - Extend: Focuses on capturing neutral bases.
        """
        def distance(base1, base2):
            return math.sqrt((base1["x"] - base2["x"])**2 + (base1["y"] - base2["y"])**2)
        
        player = game_state["player"]
        size = game_state["size"]
        game_time = game_state["game_time"]
        max_duration = game_state["game_max_duration"]
        
        bases = game_state["bases"]
        movements = game_state["movements"]
        
        # Identify enemy player
        enemy_player = 2 if player == 1 else 1
        
        # Update base histories and estimate attack probability
        my_bases = [b for b in bases if b["owner"] == player]
        enemy_bases = [b for b in bases if b["owner"] == enemy_player]

        base_threats = {}
        for my_base in my_bases:
            threat_level = 0
            base_key = (my_base["x"], my_base["y"])
            for enemy_base in enemy_bases:
                dist = distance(my_base, enemy_base)
                if dist < 4:  # Only consider nearby threats
                    threat_level += enemy_base["units"] / (dist * 1.5)
            base_threats[base_key] = threat_level
            
        for base in bases:
            key = (base["x"], base["y"])
            if key not in self.base_unit_histories:
                self.base_unit_histories[key] = []
            self.base_unit_histories[key].append(base["units"])

            # Limit history size to 10 for each base
            if len(self.base_unit_histories[key]) > 10:
                self.base_unit_histories[key].pop(0)
        
        # Identify enemy bases, neutral bases, and bases owned by the player
        enemy_bases = [b for b in bases if b["owner"] == enemy_player]
        neutral_bases = [b for b in bases if b["owner"] == 0]
        my_bases = [b for b in bases if b["owner"] == player]
        
        # Function to estimate attack probability of a base
        def get_base_threat(base):
            # Estimate attack probability based on various factors (enemy presence, history, etc.)
            prob = self.estimate_attack_probability(base, game_state, player)
            return prob
        
        # Function to calculate distance between two bases
        def distance(base1, base2):
            return math.sqrt((base1["x"] - base2["x"])**2 + (base1["y"] - base2["y"])**2)
        
        def is_speedy_base(base):
            return base.get("type", "") == "SpeedyBase"
        
        # Check if a base is a special base (high growth)
        def is_special_base(base):
            return base.get("type", "") == "SpecialBase"
        
        # Identify targets (bases that are weak, under threat, or neutral)
        targets = []
        for base in enemy_bases + neutral_bases:
            prob = get_base_threat(base)
            if base["owner"] != player and base["units"] < 10:  # Target weak or neutral bases
                targets.append((base, prob))
        
        # Sort targets by threat level (highest probability of successful attack first)
        targets.sort(key=lambda x: x[1], reverse=True)
        
        # Find my strongest base (the one with the most units)
        my_strongest_base = None
        for base in my_bases:
            if not my_strongest_base or base["units"] > my_strongest_base["units"]:
                my_strongest_base = base
        
        mode, _ = self.select_mode(game_state, player)
        if mode == "attack":
            # Attack mode: Attack the most vulnerable base (weak or neutral)
            if my_strongest_base and targets:
                target_base, prob = targets[0]  # Take the most vulnerable target
                units_to_send = min(my_strongest_base["units"] // 2, target_base["units"] + 5)
                
                if target_base["owner"] == 0:  # Neutral base
                    move = [my_strongest_base["x"], my_strongest_base["y"], target_base["x"], target_base["y"], units_to_send]
                    return {"move": move}
                elif target_base["owner"] == enemy_player:  # Enemy base
                    move = [my_strongest_base["x"], my_strongest_base["y"], target_base["x"], target_base["y"], units_to_send]
                    return {"move": move}
        
        elif mode == "defend":
            # Defend mode: Reinforce bases that are under threat
            for base in my_bases:
                threat_level = self.estimate_attack_probability(base, game_state, player)
                if threat_level > 0.5:  # Threshold for reinforcement
                    # Find the nearest base to send units from
                    if my_strongest_base:
                        units_to_send = min(my_strongest_base["units"] // 2, base["units"] + 5)
                        move = [my_strongest_base["x"], my_strongest_base["y"], base["x"], base["y"], units_to_send]
                        return {"move": move}
                
        elif mode == "extend":
            
            # Extract bases from JSON
            bases = game_state["bases"]
            
            # Get my bases, enemy bases and neutral bases
            my_bases = [b for b in bases if b["owner"] == player]
            enemy_player = 2 if player == 1 else 1
            enemy_bases = [b for b in bases if b["owner"] == enemy_player]
            neutral_bases = [b for b in bases if b["owner"] == 0]
            
            if not my_bases:
                return {"move": []}  # No bases, no moves to make
            

            base_threats = {}
            for my_base in my_bases:
                threat_level = 0
                base_key = (my_base["x"], my_base["y"])
                for enemy_base in enemy_bases:
                    dist = distance(my_base, enemy_base)
                    if dist < 4:  # Only consider nearby threats
                        threat_level += enemy_base["units"] / (dist * 1.5)
                base_threats[base_key] = threat_level
            
            # Randomly choose one of our bases to make a move from
            available_bases = [base for base in my_bases if base["units"] > 5]
            if not available_bases:
                return {"move": []}
            
            # Choose a random base with higher probability for bases with more units
            weights = [base["units"] for base in available_bases]
            total_weight = sum(weights)
            if total_weight == 0:
                return {"move": []}
            
            r = random.random() * total_weight
            cumulative_weight = 0
            base = None
            for i, b in enumerate(available_bases):
                cumulative_weight += weights[i]
                if r <= cumulative_weight:
                    base = b
                    break
            
            if not base:
                return {"move": []}
            
            base_key = (base["x"], base["y"])
            threat_level = base_threats.get(base_key, 0)
            defense_units = 5 + int(threat_level)
            available_units = max(0, base["units"] - defense_units)
            
            if available_units <= 1:
                return {"move": []}
            
            # Decide on a target and execute move
            target = None
            units_to_send = 0
            
            # Priority 1: Defend threatened bases
            if threat_level > 20 and available_units > 0:
                allies = sorted([b for b in my_bases if (b["x"], b["y"]) != (base["x"], base["y"])], 
                            key=lambda b: (distance(base, b), -b["units"]))
                if allies:
                    target = allies[0]
                    units_to_send = min(available_units, base["units"] - defense_units)
            

            # Priority 3: Capture neutral bases
            if not target and neutral_bases and available_units > 5:
                targets = sorted(neutral_bases, key=lambda b: (b["units"], distance(base, b)))
                if targets and available_units > targets[0]["units"]:
                    target = targets[0]
                    units_to_send = min(available_units, target["units"] + 5)
            
            # Priority 4: Reinforce other bases
            if not target and len(my_bases) > 1 and available_units > 10:
                allies = []
                for b in my_bases:
                    if (b["x"], b["y"]) != (base["x"], base["y"]):
                        b_key = (b["x"], b["y"])
                        if base_threats.get(b_key, 0) < 15:
                            allies.append(b)
                allies.sort(key=lambda b: b["units"])
                
                if allies and allies[0]["units"] < base["units"] - 10:
                    target = allies[0]
                    units_to_send = min(available_units, base["units"] // 2)
            
            # Priority 6: Strategic base capture for future expansion (if the game is in late stages)
            if not target and len(my_bases) < 3 and available_units > 15:
                strategic_bases = sorted(neutral_bases, key=lambda b: distance(base, b))
                if strategic_bases:
                    target = strategic_bases[0]
                    units_to_send = min(available_units, target["units"] + 5)
            
            # Priority 7: Retreat if a base is lost or under extreme threat
            if not target and base_threats.get(base_key, 0) > 40 and available_units > 0:
                # Retreat the remaining units to a safer base
                safe_bases = sorted([b for b in my_bases if base_threats.get((b["x"], b["y"]), 0) < 10],
                                    key=lambda b: distance(base, b))
                if safe_bases:
                    target = safe_bases[0]
                    units_to_send = available_units  # Send all remaining units
            
            # Execute the move if we found a target
            if target and units_to_send > 0:
                return {
                    "move": [
                        base["x"], base["y"],
                        target["x"], target["y"],
                        units_to_send
                    ]
                }
            
            return {"move": []}
                


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
