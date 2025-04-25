import socket
import json
import sys
import math
import random
import time

class GameClient:
    def __init__(self, port, player_id, player_num):
        self.port = int(port)
        self.player_id = player_id
        self.player_num = int(player_num)
        self.sock = None
        self.saved_data = {}
        self.base_movement_speed = 0.375
        self.base_type_to_production_rate = {"Base": 1, "SpecialBase": 2, "SpeedyBase": 1, "FortifiedBase": 1}
        self.base_type_to_burst_capacity = {"Base": 10, "SpecialBase": 10, "SpeedyBase": 10, "FortifiedBase": 20}
        self.base_type_to_speed_multiplier = {"Base": 1, "SpecialBase": 1, "SpeedyBase": 1.5, "FortifiedBase": 1}
    
    def connect(self):
        """Connect to the game server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(('localhost', self.port))
            print(f"Socket Player {self.player_num} connected to game server on port {self.port}")
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
                    move = self.player1_strategy(game_state, self.player_num)
                    # Send move back to server
                    move_str = json.dumps(move)
                    self.send_message(move_str + '\n')
                except json.JSONDecodeError as e:
                    print(f"JSON error: {e}")
                    break
        except Exception as e:
            print(f"Error in run loop: {e}")
            import traceback
            traceback.print_exc()
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

    # def calculate_base_score(self, base):


    def calculate_move_time(self, source_base, target_base):
        dx = abs(source_base['x'] - target_base['x'])
        dy = abs(source_base['y'] - target_base['y'])
        return (dx + dy) * self.base_movement_speed / self.base_type_to_speed_multiplier[source_base["type"]]
    
    def calculate_acquisition_time(self, source_base, target_base):
        source_produce_rate = self.base_type_to_production_rate[source_base["type"]]
        target_produce_rate = self.base_type_to_production_rate[target_base["type"]] if target_base["owner"] != 0 else 0


    def player1_strategy(self, game_state, player_num):
        """
        Player 1 strategy function that works with JSON game state
        
        Args:
            game_state: JSON dict containing all game state information
            player_num: integer representing player number (1 or 2)
            
        Returns:
            Dict containing either "move" or "moves" key with the actions to take
        """
        print(game_state)

        enemy_player_num = 2 if player_num == 1 else 1
        bases = game_state["bases"]

        my_bases = []
        enemy_bases = []
        neutral_bases = []
        for base in bases:
            if base["owner"] == player_num:
                my_bases.append(base)
            elif base["owner"] == enemy_player_num:
                enemy_bases.append(base)
            else:
                neutral_bases.append(base)
        # print("my_bases", my_bases)
        # print("enemy_bases", enemy_bases)
        # print("neutral_bases", neutral_bases)

        available_units = [my_base["units"]-1 for my_base in my_bases]
        all_available_units = sum(available_units)

        moves = []

        other_bases = enemy_bases + neutral_bases

        nearest_base = None
        if len(my_bases) < 3:

            if len(other_bases) > 0:
                move_times = {}
                for other_base_index, other_base in enumerate(other_bases):
                    move_times[other_base_index] = 0
                    for my_base_index, my_base in enumerate(my_bases):
                        move_times[other_base_index] = max(self.calculate_move_time(my_base, other_base), move_times[other_base_index])
            
                nearest_base_index = -1
                nearest_base_move_time = 999999999999999999999
                for other_base_index, other_base_move_time in move_times.items():
                    if other_base_move_time < nearest_base_move_time:
                        nearest_base_move_time = other_base_move_time
                        nearest_base_index = other_base_index
                
                if nearest_base_index != -1:
                    nearest_base = other_bases[nearest_base_index]
        else:
            other_units = [other_base["units"] for other_base in other_bases]

            nearest_base = other_bases[other_units.index(min(other_units))]

        # nearest_base = None
        # if len(other_bases) > 0:
        #     move_times = {}
        #     for other_base_index, other_base in enumerate(other_bases):
        #         move_times[other_base_index] = 0
        #         for my_base_index, my_base in enumerate(my_bases):
        #             move_times[other_base_index] = max(self.calculate_move_time(my_base, other_base), move_times[other_base_index])
        
        #     nearest_base_index = -1
        #     nearest_base_move_time = 999999999999999999999
        #     for other_base_index, other_base_move_time in move_times.items():
        #         if other_base_move_time < nearest_base_move_time:
        #             nearest_base_move_time = other_base_move_time
        #             nearest_base_index = other_base_index
            
        #     if nearest_base_index != -1:
        #         nearest_base = other_bases[nearest_base_index]


        # nearest_base = None
        # if len(neutral_bases) > 0:
        #     move_times = {}
        #     for neutral_base_index, neutral_base in enumerate(neutral_bases):
        #         move_times[neutral_base_index] = 0
        #         for my_base_index, my_base in enumerate(my_bases):
        #             move_times[neutral_base_index] = max(self.calculate_move_time(my_base, neutral_base), move_times[neutral_base_index])
        
        #     nearest_base_index = -1
        #     nearest_base_move_time = 999999999999999999999
        #     for neutral_base_index, neutral_base_move_time in move_times.items():
        #         if neutral_base_move_time < nearest_base_move_time:
        #             nearest_base_move_time = neutral_base_move_time
        #             nearest_base_index = neutral_base_index
            
        #     if nearest_base_index != -1:
        #         nearest_base = neutral_bases[nearest_base_index]
        # elif len(enemy_bases) > 0:
        #     move_times = {}
        #     for enemy_base_index, enemy_base in enumerate(enemy_bases):
        #         move_times[enemy_base_index] = 0
        #         for my_base_index, my_base in enumerate(my_bases):
        #             move_times[enemy_base_index] = max(self.calculate_move_time(my_base, enemy_base), move_times[enemy_base_index])
        
        #     nearest_base_index = -1
        #     nearest_base_move_time = 999999999999999999999
        #     for enemy_base_index, enemy_base_move_time in move_times.items():
        #         if enemy_base_move_time < nearest_base_move_time:
        #             nearest_base_move_time = enemy_base_move_time
        #             nearest_base_index = enemy_base_index
            
        #     if nearest_base_index != -1:
        #         nearest_base = enemy_bases[nearest_base_index]

        used_units = 0
        if all_available_units > nearest_base["units"]:
            for my_base in my_bases:
                print('nearest_base["units"]', nearest_base["units"])
                print('used_units', used_units)
                attack_units = min(my_base["units"]-1, nearest_base["units"]-used_units+1)
                print('attack_units', attack_units)
                moves.append([my_base["x"], my_base["y"], nearest_base["x"], nearest_base["y"], attack_units])
                used_units += attack_units
                if used_units > nearest_base["units"]:
                    break

        # if nearest_base != None:
        #     for my_base in my_bases:
        #         my_base_burst_capacity = self.base_type_to_burst_capacity[my_base["type"]]
        #         moves.append([my_base["x"], my_base["y"], nearest_base["x"], nearest_base["y"], min(nearest_base["units"]+1, math.floor(my_base["units"]/my_base_burst_capacity)*my_base_burst_capacity)])

        # for my_base in my_bases:
        #     my_base_burst_capacity = self.base_type_to_burst_capacity[my_base["type"]]
        #     # Find target
        #     nearest_base = None
        #     nearest_base_move_time = 999999999999999999999
        #     for neutral_base in neutral_bases:
        #         neutral_base_move_time = self.calculate_move_time(my_base, neutral_base)
        #         if nearest_base_move_time > neutral_base_move_time:
        #             nearest_base_move_time = neutral_base_move_time
        #             nearest_base = neutral_base
        #     if len(neutral_bases) <= 0:
        #         for enemy_base in enemy_bases:
        #             enemy_base_move_time = self.calculate_move_time(my_base, enemy_base)
        #             if nearest_base_move_time > enemy_base_move_time:
        #                 nearest_base_move_time = enemy_base_move_time
        #                 nearest_base = enemy_base
        #     if nearest_base is not None and (my_base["units"] > nearest_base["units"] or my_base["units"] >= my_base_burst_capacity):
        #         moves.append([my_base["x"], my_base["y"], nearest_base["x"], nearest_base["y"], min(nearest_base["units"]+1, math.floor(my_base["units"]/my_base_burst_capacity)*my_base_burst_capacity)])
        
        print("moves", moves)

        return {"moves": moves}

        # Convert player_num to player value
        player = player_num
        
        # Extract bases from JSON
        bases = game_state["bases"]
        
        # Get my bases, enemy bases and neutral bases
        my_bases = [b for b in bases if b["owner"] == player]
        enemy_player = 2 if player == 1 else 1
        enemy_bases = [b for b in bases if b["owner"] == enemy_player]
        neutral_bases = [b for b in bases if b["owner"] == 0]
        
        if not my_bases:
            return {"move": []}  # No bases, no moves to make
        
        # Helper to calculate distance between bases
        def distance(base1, base2):
            return math.sqrt((base1["x"] - base2["x"])**2 + (base1["y"] - base2["y"])**2)
        
        # Calculate threat levels for each base
        base_threats = {}
        for my_base in my_bases:
            threat_level = 0
            base_key = (my_base["x"], my_base["y"])
            for enemy_base in enemy_bases:
                dist = distance(my_base, enemy_base)
                if dist < 4:  # Only consider nearby threats
                    threat_level += enemy_base["units"] / (dist * 1.5)
            base_threats[base_key] = threat_level
        
        # Check if a base is a speedy base
        def is_speedy_base(base):
            return base.get("type", "") == "SpeedyBase"
        
        # Check if a base is a special base (high growth)
        def is_special_base(base):
            return base.get("type", "") == "SpecialBase"
        
        # Find any speedy bases we own
        my_speedy_bases = [base for base in my_bases if is_speedy_base(base)]
        
        # Prioritize using speedy bases if available
        available_bases = [base for base in my_bases if base["units"] > 10]
        
        # If we have a speedy base with enough units, use it with higher probability
        if my_speedy_bases and any(base["units"] > 15 for base in my_speedy_bases):
            speedy_with_units = [base for base in my_speedy_bases if base["units"] > 15]
            if random.random() < 0.7:  # 70% chance to choose a speedy base if available
                available_bases = speedy_with_units
        
        if not available_bases:
            return {"move": []}
        
        # Choose a random base with higher probability for bases with more units
        weights = [base["units"] for base in available_bases]
        # Boost weight for speedy bases
        for i, base in enumerate(available_bases):
            if is_speedy_base(base):
                weights[i] *= 1.5  # Increase probability of choosing speedy bases
        
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
        
        # Calculate how many units to send (leave some for defense)
        base_key = (base["x"], base["y"])
        threat_level = base_threats.get(base_key, 0)
        defense_units = 5 + int(threat_level)
        available_units = max(0, base["units"] - defense_units)
        
        if available_units <= 5:
            return {"move": []}
        
        # Plan multiple moves from this base
        moves_to_make = []
        units_allocated = 0
        
        # Create a list of potential targets with assigned priorities
        potential_targets = []
        
        # Look for neutral or enemy speedy/special bases - highest priority
        neutral_speedy_bases = [b for b in neutral_bases if is_speedy_base(b)]
        enemy_speedy_bases = [b for b in enemy_bases if is_speedy_base(b)]
        neutral_special_bases = [b for b in neutral_bases if is_special_base(b)]
        enemy_special_bases = [b for b in enemy_bases if is_special_base(b)]
        
        # Priority 0: Capture speedy bases (highest priority)
        if available_units > 10:
            # First neutral speedy bases (easiest to capture)
            for speedy_base in neutral_speedy_bases:
                potential_targets.append({
                    'base': speedy_base,
                    'priority': 0,  # Highest priority
                    'units': speedy_base["units"] + 10,  # Send extra units to ensure capture
                    'reason': 'capture_speedy'
                })
            
            # Then enemy speedy bases if we have enough units
            if available_units > 30:
                for speedy_base in enemy_speedy_bases:
                    if speedy_base["units"] < available_units * 0.9:
                        potential_targets.append({
                            'base': speedy_base,
                            'priority': 0,  # Highest priority
                            'units': speedy_base["units"] + 15,
                            'reason': 'attack_speedy'
                        })
        
        # Priority 1: Defend threatened bases
        if available_units > 0:
            threatened_allies = []
            for ally in my_bases:
                if (ally["x"], ally["y"]) != (base["x"], base["y"]):
                    ally_key = (ally["x"], ally["y"])
                    if base_threats.get(ally_key, 0) > 15:
                        threatened_allies.append(ally)
                        
            for ally in threatened_allies:
                ally_key = (ally["x"], ally["y"])
                potential_targets.append({
                    'base': ally,
                    'priority': 1,
                    'units': min(available_units // 3, 10 + int(base_threats.get(ally_key, 0))),
                    'reason': 'defend'
                })
        
        # Priority 2: Attack weak enemy bases
        if available_units > 10:
            weak_enemies = [b for b in enemy_bases if b["units"] < available_units * 0.8 
                          and not is_speedy_base(b) and not is_special_base(b)]
            for enemy in weak_enemies[:2]:  # Limit to 2 targets
                potential_targets.append({
                    'base': enemy,
                    'priority': 2,
                    'units': enemy["units"] + 5,
                    'reason': 'attack'
                })
        
        # Priority 3: Capture neutral bases
        if available_units > 15:
            close_neutrals = sorted([b for b in neutral_bases 
                                   if b["units"] < available_units * 0.7
                                   and not is_speedy_base(b) and not is_special_base(b)], 
                                  key=lambda b: (distance(base, b), b["units"]))
            for neutral in close_neutrals[:2]:  # Limit to 2 targets
                potential_targets.append({
                    'base': neutral,
                    'priority': 3,
                    'units': neutral["units"] + 3,
                    'reason': 'capture'
                })
        
        # Priority 4: Reinforce weak allies
        if available_units > 20:
            weak_allies = [b for b in my_bases if (b["x"], b["y"]) != (base["x"], base["y"]) 
                         and b["units"] < base["units"] * 0.5]
            for ally in weak_allies[:1]:  # Limit to 1 target
                potential_targets.append({
                    'base': ally,
                    'priority': 4,
                    'units': min(available_units // 4, 15),
                    'reason': 'reinforce'
                })
        
        # Sort targets by priority
        potential_targets.sort(key=lambda t: (t['priority'], -t['units']))
        
        # Create moves until we run out of units or targets
        for target_info in potential_targets:
            target = target_info['base']
            units_to_send = min(target_info['units'], available_units - units_allocated)
            
            if units_to_send > 3:  # Only make meaningful moves
                moves_to_make.append([
                    base["x"], base["y"],
                    target["x"], target["y"],
                    units_to_send
                ])
                units_allocated += units_to_send
                
                # Stop if we've allocated most of our available units
                if units_allocated > available_units * 0.9:
                    break
        
        # Execute the multi-move if we have moves to make
        if moves_to_make:
            return {"moves": moves_to_make}
        
        # Fall back to original strategy if no multi-moves were planned
        return self.original_better_ai_play(game_state, player_num)

    def original_better_ai_play(self, game_state, player_num):
        """Original strategy as a fallback"""
        player = player_num
        
        # Extract bases from JSON
        bases = game_state["bases"]
        
        # Get my bases, enemy bases and neutral bases
        my_bases = [b for b in bases if b["owner"] == player]
        enemy_player = 2 if player == 1 else 1
        enemy_bases = [b for b in bases if b["owner"] == enemy_player]
        neutral_bases = [b for b in bases if b["owner"] == 0]
        
        if not my_bases:
            return {"move": []}  # No bases, no moves to make
        
        # Helper to calculate distance between bases
        def distance(base1, base2):
            return math.sqrt((base1["x"] - base2["x"])**2 + (base1["y"] - base2["y"])**2)
        
        # Calculate threat levels for each base
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
        
        # Calculate how many units to send (leave some for defense)
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
        
        # Priority 2: Attack weak enemy bases
        if not target and enemy_bases and available_units > 10:
            targets = sorted(enemy_bases, key=lambda b: (b["units"], distance(base, b)))
            if targets and available_units > targets[0]["units"]:
                target = targets[0]
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
        
        # Priority 5: Attack any enemy base if we have overwhelming force
        if not target and enemy_bases and available_units > 25:
            targets = sorted(enemy_bases, key=lambda b: (distance(base, b), b["units"]))
            if targets:
                target = targets[0]
                units_to_send = min(available_units, base["units"] - defense_units)
        
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
    if len(sys.argv) < 4:
        print("Usage: python socket_player1.py <port> <player_id> <player_num>")
        sys.exit(1)
    
    port = sys.argv[1]
    player_id = sys.argv[2]
    player_num = sys.argv[3]
    
    client = GameClient(port, player_id, player_num)
    
    if not client.connect():
        sys.exit(1)
    
    client.run()

if __name__ == "__main__":
    main()
