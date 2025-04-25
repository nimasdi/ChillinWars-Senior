import socket
import json
import sys
import math
import random
import time
from collections import defaultdict

class StrongAIPlayer:
    def __init__(self, port, player_id, player_num):
        self.port = int(port)
        self.player_id = player_id
        self.player_num = int(player_num)
        self.sock = None
        self.game_history = []
        self.opponent_profile = {
            'aggression': 0.5,
            'expansion': 0.5,
            'defense': 0.5
        }
        self.last_move_time = time.time()
        self.strategy_phase = "early"  # early, mid, late
        self.special_bases_owned = 0

    def connect(self):
        """Connect to the game server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(('localhost', self.port))
            print(f"Strong AI Player {self.player_num} connected to game server")
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def run(self):
        """Main game loop"""
        try:
            while True:
                game_state_str = self.receive_message()
                if not game_state_str:
                    break
                
                game_state = json.loads(game_state_str)
                self.analyze_opponent(game_state)
                self.update_strategy_phase(game_state)
                
                move = self.decide_move(game_state)
                self.send_message(json.dumps(move) + '\n')
                
                # Store game state for analysis
                self.game_history.append(game_state)
                
        except Exception as e:
            print(f"Error in game loop: {e}")
        finally:
            self.close()

    def receive_message(self):
        """Receive complete message from server"""
        result = b""
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            result += chunk
            if b"\n" in chunk:
                break
        return result.decode().strip()

    def send_message(self, message):
        """Send message to server"""
        try:
            self.sock.sendall(message.encode())
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False

    def close(self):
        """Clean up connection"""
        if self.sock:
            self.sock.close()

    def analyze_opponent(self, game_state):
        """Analyze opponent behavior patterns"""
        if len(self.game_history) < 2:
            return
            
        prev_state = self.game_history[-1]
        current_state = game_state
        
        # Calculate opponent's aggression
        enemy_movements = [m for m in current_state["movements"] 
                          if m["owner"] != self.player_num]
        
        if enemy_movements:
            total_aggression = sum(m["units"] for m in enemy_movements)
            self.opponent_profile['aggression'] = 0.9 * self.opponent_profile['aggression'] + 0.1 * (total_aggression / 100)
        
        # Calculate opponent's expansion rate
        enemy_bases = [b for b in current_state["bases"] 
                      if b["owner"] != self.player_num and b["owner"] != 0]
        prev_enemy_bases = [b for b in prev_state["bases"] 
                           if b["owner"] != self.player_num and b["owner"] != 0]
        
        if prev_enemy_bases:
            expansion_rate = (len(enemy_bases) - len(prev_enemy_bases)) / len(prev_enemy_bases)
            self.opponent_profile['expansion'] = 0.9 * self.opponent_profile['expansion'] + 0.1 * expansion_rate
        
        # Calculate opponent's defensive strength
        enemy_lost_bases = [b for b in prev_state["bases"] 
                           if b["owner"] != self.player_num and b["owner"] != 0
                           and not any(b2["x"] == b["x"] and b2["y"] == b["y"] 
                                      for b2 in current_state["bases"] 
                                      if b2["owner"] == b["owner"])]
        
        if enemy_movements:
            defense_score = 1 - (len(enemy_lost_bases) / len(enemy_movements))
            self.opponent_profile['defense'] = 0.9 * self.opponent_profile['defense'] + 0.1 * defense_score

    def update_strategy_phase(self, game_state):
        """Determine current game phase based on game state"""
        game_time = game_state["game_time"]
        max_duration = game_state["game_max_duration"]
        
        # Count special bases we own
        self.special_bases_owned = sum(
            1 for b in game_state["bases"] 
            if b["owner"] == self.player_num and 
            b.get("type") in ["SpeedyBase", "FortifiedBase", "SpecialBase"]
        )
        
        if game_time < max_duration * 0.3:
            self.strategy_phase = "early"
        elif game_time < max_duration * 0.7:
            self.strategy_phase = "mid"
        else:
            self.strategy_phase = "late"

    def decide_move(self, game_state):
        """Main decision making function"""
        player = self.player_num
        bases = game_state["bases"]
        movements = game_state["movements"]
        size = game_state["size"]
        
        # Get all relevant bases
        my_bases = [b for b in bases if b["owner"] == player]
        enemy_bases = [b for b in bases if b["owner"] not in [player, 0]]
        neutral_bases = [b for b in bases if b["owner"] == 0]
        
        # Special bases
        speedy_bases = [b for b in bases if b.get("type") == "SpeedyBase"]
        fortified_bases = [b for b in bases if b.get("type") == "FortifiedBase"]
        special_bases = [b for b in bases if b.get("type") == "SpecialBase"]
        
        # Calculate distances between all bases
        def distance(base1, base2):
            return math.sqrt((base1["x"] - base2["x"])**2 + (base1["y"] - base2["y"])**2)
        
        # Early game: Focus on expansion and capturing special bases
        if self.strategy_phase == "early":
            return self.early_game_strategy(my_bases, neutral_bases, speedy_bases, 
                                          fortified_bases, special_bases, distance)
        
        # Mid game: Consolidate and prepare for late game
        elif self.strategy_phase == "mid":
            return self.mid_game_strategy(my_bases, enemy_bases, neutral_bases, 
                                        speedy_bases, fortified_bases, special_bases, 
                                        distance)
        
        # Late game: Full-scale assault
        else:
            return self.late_game_strategy(my_bases, enemy_bases, distance)

    def early_game_strategy(self, my_bases, neutral_bases, speedy_bases, 
                          fortified_bases, special_bases, distance_func):
        """Strategy for the early game phase"""
        moves = []
        
        # Prioritize capturing special bases first
        for base in my_bases:
            if base["units"] < 15:
                continue  # Not enough units to send
                
            # Find closest special base
            targets = []
            
            # Speedy bases are highest priority
            targets.extend([(b, 0) for b in speedy_bases if b["owner"] != self.player_num])
            # Then special growth bases
            targets.extend([(b, 1) for b in special_bases if b["owner"] != self.player_num])
            # Then fortified bases
            targets.extend([(b, 2) for b in fortified_bases if b["owner"] != self.player_num])
            # Then regular neutral bases
            targets.extend([(b, 3) for b in neutral_bases])
            
            # Sort by priority and distance
            targets.sort(key=lambda x: (x[1], distance_func(base, x[0])))
            
            if targets:
                target = targets[0][0]
                units_to_send = min(
                    base["units"] - 5,  # Always leave some defense
                    target["units"] + 5 if target["owner"] == 0 else target["units"] + 10
                )
                
                if units_to_send > 5:
                    moves.append([
                        base["x"], base["y"],
                        target["x"], target["y"],
                        units_to_send
                    ])
        
        # If we have multiple moves, return them all
        if moves:
            return {"moves": moves[:3]}  # Limit to 3 moves per turn
        
        # Fallback: if no special bases to capture, just expand
        return self.expansion_strategy(my_bases, neutral_bases, distance_func)

    def mid_game_strategy(self, my_bases, enemy_bases, neutral_bases, 
                         speedy_bases, fortified_bases, special_bases, distance_func):
        """Strategy for the mid game phase"""
        moves = []
        
        # 1. Reinforce our special bases
        for base in my_bases:
            if base["units"] < 20:
                continue  # Not strong enough to send
                
            # Find our special bases that need reinforcement
            our_special_bases = [
                b for b in my_bases 
                if b != base and 
                b.get("type") in ["SpeedyBase", "FortifiedBase", "SpecialBase"] and
                b["units"] < 30
            ]
            
            if our_special_bases:
                # Find closest special base that needs help
                our_special_bases.sort(key=lambda b: distance_func(base, b))
                target = our_special_bases[0]
                units_to_send = min(base["units"] - 10, 15)  # Send up to 15 units
                
                if units_to_send > 5:
                    moves.append([
                        base["x"], base["y"],
                        target["x"], target["y"],
                        units_to_send
                    ])
        
        # 2. Attack enemy special bases if we can
        for base in my_bases:
            if base["units"] < 25:
                continue
                
            # Find enemy special bases
            enemy_special_bases = [
                b for b in enemy_bases 
                if b.get("type") in ["SpeedyBase", "FortifiedBase", "SpecialBase"]
            ]
            
            if enemy_special_bases:
                # Find weakest enemy special base within range
                enemy_special_bases.sort(key=lambda b: (b["units"], distance_func(base, b)))
                target = enemy_special_bases[0]
                
                if distance_func(base, target) < 5:  # Only attack if reasonably close
                    units_to_send = min(
                        base["units"] - 10,
                        target["units"] + 15
                    )
                    
                    if units_to_send > 10:
                        moves.append([
                            base["x"], base["y"],
                            target["x"], target["y"],
                            units_to_send
                        ])
        
        # 3. Continue expanding if we have resources
        if len(moves) < 2:  # If we haven't made many moves yet
            expansion_moves = self.expansion_strategy(my_bases, neutral_bases, distance_func)
            if "moves" in expansion_moves:
                moves.extend(expansion_moves["moves"])
        
        if moves:
            return {"moves": moves[:4]}  # Limit to 4 moves per turn
        
        # Fallback: if nothing else, prepare for late game
        return self.prepare_for_late_game(my_bases, distance_func)

    def late_game_strategy(self, my_bases, enemy_bases, distance_func):
        """Strategy for the late game phase"""
        moves = []
        
        # 1. Identify enemy's strongest base
        if enemy_bases:
            enemy_bases.sort(key=lambda b: -b["units"])
            main_target = enemy_bases[0]
            
            # 2. Coordinate attack from multiple bases
            attacking_bases = []
            for base in my_bases:
                if base["units"] > 20 and distance_func(base, main_target) < 6:
                    attacking_bases.append(base)
            
            # Sort by strength (strongest first)
            attacking_bases.sort(key=lambda b: -b["units"])
            
            # Assign units to attack
            for base in attacking_bases[:3]:  # Max 3 bases attack together
                units_to_send = min(
                    base["units"] - 10,
                    int(base["units"] * 0.7)
                )
                
                if units_to_send > 15:
                    moves.append([
                        base["x"], base["y"],
                        main_target["x"], main_target["y"],
                        units_to_send
                    ])
        
        # 3. Clean up remaining enemy bases
        if len(moves) < 2:  # If we're not doing a coordinated attack
            for base in my_bases:
                if base["units"] < 15:
                    continue
                    
                # Find closest enemy base
                nearby_enemies = [
                    b for b in enemy_bases 
                    if distance_func(base, b) < 4
                ]
                
                if nearby_enemies:
                    nearby_enemies.sort(key=lambda b: (b["units"], distance_func(base, b)))
                    target = nearby_enemies[0]
                    
                    units_to_send = min(
                        base["units"] - 5,
                        target["units"] + 10
                    )
                    
                    if units_to_send > 5:
                        moves.append([
                            base["x"], base["y"],
                            target["x"], target["y"],
                            units_to_send
                        ])
        
        if moves:
            return {"moves": moves[:5]}  # Limit to 5 moves per turn
        
        # Fallback: if no enemies left, just reinforce
        return {"moves": []}

    def expansion_strategy(self, my_bases, neutral_bases, distance_func):
        """Basic expansion strategy to capture neutral bases"""
        moves = []
        
        for base in my_bases:
            if base["units"] < 10:
                continue
                
            # Find closest neutral base
            if neutral_bases:
                neutral_bases.sort(key=lambda b: (distance_func(base, b), b["units"]))
                target = neutral_bases[0]
                
                units_to_send = min(
                    base["units"] - 5,
                    target["units"] + 3
                )
                
                if units_to_send > 1:
                    moves.append([
                        base["x"], base["y"],
                        target["x"], target["y"],
                        units_to_send
                    ])
        
        if moves:
            return {"moves": moves[:2]}  # Limit to 2 expansion moves per turn
        return {"moves": []}

    def prepare_for_late_game(self, my_bases, distance_func):
        """Prepare for late game by consolidating forces"""
        moves = []
        
        # Find our strongest base
        if len(my_bases) > 1:
            my_bases.sort(key=lambda b: -b["units"])
            main_base = my_bases[0]
            
            # Have other bases send reinforcements
            for base in my_bases[1:]:
                if base["units"] > 10 and distance_func(base, main_base) < 5:
                    units_to_send = min(base["units"] - 5, 15)
                    
                    if units_to_send > 5:
                        moves.append([
                            base["x"], base["y"],
                            main_base["x"], main_base["y"],
                            units_to_send
                        ])
        
        if moves:
            return {"moves": moves[:3]}  # Limit to 3 reinforcement moves
        return {"moves": []}

def main():
    if len(sys.argv) < 4:
        print("Usage: python strong_ai_player.py <port> <player_id> <player_num>")
        sys.exit(1)
    
    port = sys.argv[1]
    player_id = sys.argv[2]
    player_num = sys.argv[3]
    
    player = StrongAIPlayer(port, player_id, player_num)
    
    if not player.connect():
        sys.exit(1)
    
    player.run()

if __name__ == "__main__":
    main()