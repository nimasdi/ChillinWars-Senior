import socket
import json
import sys
import math
import random
import time
from collections import defaultdict
from typing import List, Dict, Tuple, Set

class StrategicPlayer:
    def __init__(self, port, player_id, player_num):
        self.port = port
        self.player_id = player_id
        self.player_num = player_num
        self.sock = None
        
        # Game state tracking
        self.last_move_time = defaultdict(float)
        self.base_priorities = {}
        self.fort_node = -1
        self.fort_troops = 0
        self.fort_turn = -1
        self.successful_attack = False
        self.turn_number = 0
        self.previous_neutral_bases = set()  # Track neutral bases from previous turn
        self.contested_bases = set()  # Track bases being contested by enemy
        self.path_cache = {}  # Cache for path distances
        
        # Strategy parameters
        self.defensive_threshold = 15
        self.aggressive_threshold = 0.7
        self.attack_threshold = 0.6  # Lowered for more aggressive attacks
        self.strategic_instability_threshold = 0.5
        self.fast_attack_threshold = 0.7
        self.first_defense_threshold = 0.5
        self.second_defense_threshold = 0.75
        
        # Unit advantage parameters
        self.unit_advantage_threshold = 2.0  # Attack when we have 2x more units
        self.unit_advantage_attack_threshold = 0.4  # Lower threshold when we have unit advantage
        
        # Movement rates for different scenarios
        self.move_rate = 0.6
        self.move_rate_to_strategic = 0.8
        self.move_rate_from_strategic = 0.3
        self.move_rate_to_strategic_from_strategic = 0.55
        self.return_rate = 1.0
        
        # Other parameters
        self.failure_probability_threshold = 0.05
        self.max_soldiers = 100  # Maximum units a base can hold
        self.min_soldiers = 1
        self.max_distance = 20
        self.max_capacity_threshold = 80  # Start distributing at 80 units
        self.distribution_ratio = 0.7  # Increased from 0.5 to distribute more units
        self.min_units_for_attack = 5  # Minimum units required to consider an attack
        self.nearby_base_threshold = 5  # Distance considered "nearby" for priority attacks
        self.nearby_base_priority = 2.0  # Priority multiplier for nearby bases
        self.min_units_to_distribute = 10  # Minimum units to distribute at once
        
        # Opening phase parameters
        self.opening_phase_turns = 20  # Number of turns considered opening phase
        self.contested_base_priority = 2.0  # Priority multiplier for contested bases
        self.min_units_for_contested = 3  # Minimum units needed to capture contested base
    
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
                game_state_str = self.receive_message()
                if not game_state_str:
                    break
                
                try:
                    game_state = json.loads(game_state_str)
                    move = self.make_move(game_state)
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
    
    def get_neighbors(self, x, y, size):
        """Get valid neighboring positions in the grid"""
        neighbors = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:  # Only orthogonal moves
            nx, ny = x + dx, y + dy
            if 0 <= nx < size and 0 <= ny < size:
                neighbors.append((nx, ny))
        return neighbors

    def dfs_path_distance(self, start, end, size, visited=None, path=None):
        """Calculate the shortest path distance between two points using DFS"""
        if visited is None:
            visited = set()
        if path is None:
            path = []
        
        start_pos = (start["x"], start["y"])
        end_pos = (end["x"], end["y"])
        
        # Check cache first
        cache_key = (start_pos, end_pos)
        if cache_key in self.path_cache:
            return self.path_cache[cache_key]
        
        if start_pos == end_pos:
            return len(path)
        
        visited.add(start_pos)
        min_distance = float('inf')
        
        for neighbor in self.get_neighbors(start_pos[0], start_pos[1], size):
            if neighbor not in visited:
                new_path = path + [neighbor]
                distance = self.dfs_path_distance(
                    {"x": neighbor[0], "y": neighbor[1]},
                    end,
                    size,
                    visited.copy(),
                    new_path
                )
                min_distance = min(min_distance, distance)
        
        # Cache the result
        self.path_cache[cache_key] = min_distance
        return min_distance

    def calculate_path_distance(self, base1, base2, game_state):
        """Calculate the actual path distance between two bases"""
        size = game_state["size"]
        return self.dfs_path_distance(base1, base2, size)

    def calculate_base_value(self, base, game_state):
        """Calculate the strategic value of a base with enhanced metrics"""
        player = game_state["player"]
        bases = game_state["bases"]
        size = game_state["size"]
        
        value = 0
        
        # 1. Base type value
        base_type = base.get("type", "Base")  # Default to regular base if type not specified
        if base_type == "SpecialBase":
            value += 30  # High value for special bases (2 soldiers per second)
        elif base_type == "SpeedyBase":
            value += 21  # High value for speedy bases (1.5x speed)
        else:
            value += 10  # Regular base value
        
        # 2. Enhanced unit count value
        value += base["units"] * 0.5
        
        # 3. Position value with quadrant analysis
        center_x, center_y = size // 2, size // 2
        distance_from_center = self.calculate_path_distance(
            base,
            {"x": center_x, "y": center_y},
            game_state
        )
        value += (size - distance_from_center) * 2
        
        # 4. Proximity to enemy bases with threat assessment
        enemy_bases = [b for b in bases if b["owner"] not in [0, player]]
        if enemy_bases:
            min_enemy_distance = min(
                self.calculate_path_distance(base, e, game_state)
                for e in enemy_bases
            )
            value -= min_enemy_distance * 0.5
        
        # 5. Proximity to neutral bases with expansion potential
        neutral_bases = [b for b in bases if b["owner"] == 0]
        if neutral_bases:
            min_neutral_distance = min(
                self.calculate_path_distance(base, n, game_state)
                for n in neutral_bases
            )
            value += (size - min_neutral_distance) * 1.5
        
        # 6. Strategic position value
        if base["x"] == 0 or base["x"] == size - 1 or base["y"] == 0 or base["y"] == size - 1:
            value += 10  # Edge bases are valuable for control
        
        # 7. Proximity to our bases (for enemy bases)
        if base["owner"] not in [0, player]:
            my_bases = [b for b in bases if b["owner"] == player]
            if my_bases:
                min_my_distance = min(
                    self.calculate_path_distance(base, b, game_state)
                    for b in my_bases
                )
                if min_my_distance <= self.nearby_base_threshold:
                    value *= self.nearby_base_priority
        
        return value
    
    def calculate_instability(self, base, game_state, ignore_bases=None):
        """Calculate the instability of a base with threat assessment"""
        if ignore_bases is None:
            ignore_bases = []
        
        player = game_state["player"]
        bases = game_state["bases"]
        
        # Calculate threat from enemy bases
        threat = 0
        for enemy_base in [b for b in bases if b["owner"] not in [0, player] and b not in ignore_bases]:
            distance = self.calculate_path_distance(base, enemy_base, game_state)
            if distance <= self.max_distance:
                threat += enemy_base["units"] / (distance + 1)
        
        # Calculate defensive capability
        defense = base["units"]
        for friendly_base in [b for b in bases if b["owner"] == player and b != base]:
            distance = self.calculate_path_distance(base, friendly_base, game_state)
            if distance <= self.max_distance:
                defense += friendly_base["units"] / (distance + 1)
        
        return threat / (defense + 1)
    
    def is_good_to_attack(self, defender_units, attacker_units, is_strategic=False, base_type="Base"):
        """Determine if an attack is likely to succeed with probability analysis"""
        # Adjust attack threshold based on base type
        base_type_multiplier = 1.0
        if base_type == "SpecialBase":
            base_type_multiplier = 1.3  # Higher threshold for special bases
        elif base_type == "FortifiedBase":
            base_type_multiplier = 1.  # Higher threshold for fortified bases
        elif base_type == "SpeedyBase":
            base_type_multiplier = 1.15  # Slightly higher threshold for speedy bases
        
        adjusted_threshold = self.attack_threshold * base_type_multiplier
        
        if is_strategic:
            return (attacker_units / (defender_units + 1)) >= adjusted_threshold and \
                   (attacker_units - defender_units) * self.move_rate_from_strategic >= self.min_soldiers
        return (attacker_units / (defender_units + 1)) >= adjusted_threshold and \
               (attacker_units - defender_units) * self.move_rate >= self.min_soldiers
    
    def get_strategic_bases(self, game_state):
        """Get all strategic bases owned by the player"""
        return [b for b in game_state["bases"] 
                if b["owner"] == game_state["player"] and 
                self.calculate_base_value(b, game_state) > self.strategic_instability_threshold]
    
    def arrange_soldiers(self, game_state):
        """Arrange soldiers in the initial phase"""
        moves = []
        my_bases = [b for b in game_state["bases"] if b["owner"] == game_state["player"]]
        neutral_bases = [b for b in game_state["bases"] if b["owner"] == 0]
        
        # Find empty strategic nodes
        empty_strategic = [b for b in neutral_bases 
                          if self.calculate_base_value(b, game_state) > self.strategic_instability_threshold]
        
        if empty_strategic:
            # Sort by strategic value
            empty_strategic.sort(key=lambda b: self.calculate_base_value(b, game_state), reverse=True)
            target = empty_strategic[0]
            moves.append([
                my_bases[0]["x"],
                my_bases[0]["y"],
                target["x"],
                target["y"],
                self.min_soldiers
            ])
            return moves
        
        # Defend strategic nodes
        strategic_nodes = self.get_strategic_bases(game_state)
        if strategic_nodes:
            strategic_nodes.sort(key=lambda b: self.calculate_instability(b, game_state))
            most_threatened = strategic_nodes[0]
            
            if self.calculate_instability(most_threatened, game_state) > self.first_defense_threshold:
                # Find nearest base to reinforce
                for base in my_bases:
                    if base != most_threatened:
                        distance = self.calculate_path_distance(base, most_threatened, game_state)
                        if distance <= self.max_distance:
                            units_to_send = min(base["units"] - self.defensive_threshold,
                                              most_threatened["units"] + 5)
                            if units_to_send > 0:
                                moves.append([
                                    base["x"],
                                    base["y"],
                                    most_threatened["x"],
                                    most_threatened["y"],
                                    units_to_send
                                ])
                                break
        
        return moves
    
    def defense_strategic_nodes(self, game_state):
        """Defend strategic nodes with enhanced coordination"""
        moves = []
        strategic_nodes = self.get_strategic_bases(game_state)
        
        for node in strategic_nodes:
            instability = self.calculate_instability(node, game_state)
            if instability > self.first_defense_threshold:
                # Find nearest base to reinforce
                for base in [b for b in game_state["bases"] if b["owner"] == game_state["player"]]:
                    if base != node:
                        distance = self.calculate_path_distance(base, node, game_state)
                        if distance <= self.max_distance:
                            units_to_send = min(base["units"] - self.defensive_threshold,
                                              node["units"] + 5)
                            if units_to_send > 0:
                                moves.append([
                                    base["x"],
                                    base["y"],
                                    node["x"],
                                    node["y"],
                                    units_to_send
                                ])
                                break
        
        return moves
    
    def fast_attack(self, game_state):
        """Execute fast attacks on strategic targets"""
        moves = []
        time_progress = game_state["game_time"] / game_state["game_max_duration"]
        
        if time_progress > self.fast_attack_threshold:
            strategic_targets = [b for b in game_state["bases"] 
                               if b["owner"] not in [0, game_state["player"]] and 
                               self.calculate_base_value(b, game_state) > self.strategic_instability_threshold]
            
            for target in strategic_targets:
                for source in [b for b in game_state["bases"] if b["owner"] == game_state["player"]]:
                    if source["units"] > self.defensive_threshold:
                        distance = self.calculate_path_distance(source, target, game_state)
                        if distance <= self.max_distance:
                            units_to_send = min(source["units"] - self.defensive_threshold + 1,
                                              target["units"] + 6)
                            if self.is_good_to_attack(target["units"], units_to_send, True):
                                moves.append([
                                    source["x"],
                                    source["y"],
                                    target["x"],
                                    target["y"],
                                    units_to_send
                                ])
                                return moves
        
        return moves
    
    def is_opening_phase(self):
        """Check if we're in the opening phase of the game"""
        return self.turn_number <= self.opening_phase_turns

    def update_contested_bases(self, game_state):
        """Update the set of contested bases (neutral bases being captured by enemy)"""
        current_neutral_bases = {(b["x"], b["y"]) for b in game_state["bases"] if b["owner"] == 0}
        
        # Find bases that were neutral last turn but are now enemy
        newly_captured = self.previous_neutral_bases - current_neutral_bases
        enemy_bases = {(b["x"], b["y"]) for b in game_state["bases"] 
                      if b["owner"] not in [0, game_state["player"]]}
        
        # Update contested bases (newly captured by enemy)
        self.contested_bases = newly_captured.intersection(enemy_bases)
        
        # Update previous neutral bases for next turn
        self.previous_neutral_bases = current_neutral_bases

    def calculate_contested_base_value(self, base, game_state):
        """Calculate the value of a contested base"""
        value = self.calculate_base_value(base, game_state)
        
        # Add bonus for contested bases in opening phase
        if self.is_opening_phase():
            value *= self.contested_base_priority
        
        # Add bonus based on base type
        base_type = base.get("type", "Base")
        if base_type == "SpecialBase":
            value *= 1.5
        elif base_type == "SpeedyBase":
            value *= 1.3
        elif base_type == "FortifiedBase":
            value *= 1.1
        
        return value

    def calculate_unit_advantage(self, game_state):
        """Calculate the ratio of our units to enemy units"""
        my_units = sum(b["units"] for b in game_state["bases"] if b["owner"] == game_state["player"])
        enemy_units = sum(b["units"] for b in game_state["bases"] if b["owner"] not in [0, game_state["player"]])
        return my_units / (enemy_units + 1)  # Add 1 to avoid division by zero

    def handle_max_capacity_base(self, base, game_state):
        """Handle a base that has reached or is near maximum capacity"""
        moves = []
        my_bases = [b for b in game_state["bases"] if b["owner"] == game_state["player"]]
        enemy_bases = [b for b in game_state["bases"] if b["owner"] not in [0, game_state["player"]]]
        neutral_bases = [b for b in game_state["bases"] if b["owner"] == 0]
        
        # Calculate excess units
        excess_units = base["units"] - self.max_capacity_threshold
        if excess_units <= 0:
            return moves
        
        # Calculate unit advantage
        unit_advantage = self.calculate_unit_advantage(game_state)
        
        # Adjust attack threshold based on unit advantage
        current_attack_threshold = self.attack_threshold
        if unit_advantage >= self.unit_advantage_threshold:
            current_attack_threshold = self.unit_advantage_attack_threshold
        
        # Try to attack enemy bases first
        best_enemy_target = None
        best_enemy_value = float('-inf')
        
        for target in enemy_bases:
            distance = self.calculate_path_distance(base, target, game_state)
            if distance <= self.max_distance:
                # Calculate required units for attack
                required_units = target["units"] + 4  # Reduced from +5 to be more aggressive
                if excess_units >= required_units:
                    target_value = self.calculate_base_value(target, game_state)
                    target_value /= (distance + 1)
                    
                    # Prioritize special bases
                    if target.get("type") == "SpecialBase":
                        target_value *= 2.0
                    elif target.get("type") == "SpeedyBase":
                        target_value *= 1.5
                    elif target.get("type") == "FortifiedBase":
                        target_value *= 1.1
                    
                    if target_value > best_enemy_value:
                        best_enemy_value = target_value
                        best_enemy_target = target
        
        if best_enemy_target:
            # Attack the best enemy target
            units_to_send = min(excess_units + 1, best_enemy_target["units"] + 4)  # Reduced from +5
            moves.append([
                base["x"],
                base["y"],
                best_enemy_target["x"],
                best_enemy_target["y"],
                units_to_send
            ])
            return moves
        
        # If no good enemy target, try to capture neutral bases
        best_neutral_target = None
        best_neutral_value = float('-inf')
        
        for target in neutral_bases:
            distance = self.calculate_path_distance(base, target, game_state)
            if distance <= self.max_distance:
                if excess_units >= target["units"] + 3:  # Reduced from +4 to be more aggressive
                    target_value = self.calculate_base_value(target, game_state)
                    target_value /= (distance + 1)
                    
                    # Prioritize special bases
                    if target.get("type") == "SpecialBase":
                        target_value *= 2.0
                    elif target.get("type") == "SpeedyBase":
                        target_value *= 1.5
                    elif target.get("type") == "FortifiedBase":
                        target_value *= 1.1
                    
                    if target_value > best_neutral_value:
                        best_neutral_value = target_value
                        best_neutral_target = target
        
        if best_neutral_target:
            # Capture the best neutral target
            units_to_send = min(excess_units + 1, best_neutral_target["units"] + 3)  # Reduced from +4
            moves.append([
                base["x"],
                base["y"],
                best_neutral_target["x"],
                best_neutral_target["y"],
                units_to_send
            ])
            return moves
        
        # If no good targets, distribute units to friendly bases
        best_friendly_target = None
        best_friendly_value = float('-inf')
        
        for target in my_bases:
            if target == base:
                continue
            
            distance = self.calculate_path_distance(base, target, game_state)
            if distance <= self.max_distance:
                # Calculate how many units the target needs
                needed_units = self.max_capacity_threshold - target["units"]
                if needed_units >= self.min_units_to_distribute:
                    # Calculate value based on base type and distance
                    target_value = self.calculate_base_value(target, game_state)
                    
                    # Prioritize special bases for reinforcement
                    if target.get("type") == "SpecialBase":
                        target_value *= 2.0
                    elif target.get("type") == "SpeedyBase":
                        target_value *= 1.5
                    elif target.get("type") == "FortifiedBase":
                        target_value *= 1.1
                    
                    target_value *= (needed_units / self.max_capacity_threshold)
                    target_value /= (distance + 1)
                    
                    if target_value > best_friendly_value:
                        best_friendly_value = target_value
                        best_friendly_target = target
        
        if best_friendly_target:
            # Distribute units to the best friendly target
            units_to_send = min(excess_units, self.max_capacity_threshold - best_friendly_target["units"])
            if units_to_send >= self.min_units_to_distribute:
                moves.append([
                    base["x"],
                    base["y"],
                    best_friendly_target["x"],
                    best_friendly_target["y"],
                    units_to_send
                ])
        
        return moves

    def make_move(self, game_state):
        """Implement advanced strategy with phase management"""
        moves = []
        current_time = time.time()
        self.turn_number += 1
        
        try:
            # Clear path cache at the start of each turn
            self.path_cache = {}
            
            # Calculate unit advantage
            unit_advantage = self.calculate_unit_advantage(game_state)
            
            # Update contested bases
            self.update_contested_bases(game_state)
            
            # Check for bases at or near maximum capacity
            my_bases = [b for b in game_state["bases"] if b["owner"] == game_state["player"]]
            for base in my_bases:
                if base["units"] >= self.max_capacity_threshold:
                    capacity_moves = self.handle_max_capacity_base(base, game_state)
                    if capacity_moves:
                        moves.extend(capacity_moves)
                        return {"moves": moves}
            
            # Initial arrangement
            if self.turn_number == 1:
                moves.extend(self.arrange_soldiers(game_state))
            
            # Defensive phase
            moves.extend(self.defense_strategic_nodes(game_state))
            
            # Fast attack phase
            if not moves:
                moves.extend(self.fast_attack(game_state))
            
            # Offensive phase
            if not moves:
                time_progress = game_state["game_time"] / game_state["game_max_duration"]
                enemy_bases = [b for b in game_state["bases"] if b["owner"] not in [0, game_state["player"]]]
                neutral_bases = [b for b in game_state["bases"] if b["owner"] == 0]
                
                # Adjust attack threshold based on unit advantage
                current_attack_threshold = self.attack_threshold
                if unit_advantage >= self.unit_advantage_threshold:
                    current_attack_threshold = self.unit_advantage_attack_threshold
                
                # Prioritize contested bases in opening phase
                if self.is_opening_phase() and self.contested_bases:
                    contested_targets = [b for b in enemy_bases 
                                       if (b["x"], b["y"]) in self.contested_bases]
                    
                    for source_base in my_bases:
                        if current_time - self.last_move_time[(source_base["x"], source_base["y"])] < 0.3:
                            continue
                        
                        available_units = max(0, source_base["units"] - self.defensive_threshold)
                        if available_units < self.min_units_for_contested:
                            continue
                        
                        best_contested = None
                        best_value = float('-inf')
                        
                        for target in contested_targets:
                            distance = self.calculate_path_distance(source_base, target, game_state)
                            
                            if distance > self.max_distance:
                                continue
                            
                            if available_units >= target["units"] + self.min_units_for_contested:
                                target_value = self.calculate_contested_base_value(target, game_state)
                                target_value /= (distance + 1)
                                
                                if target_value > best_value:
                                    best_value = target_value
                                    best_contested = target
                        
                        if best_contested:
                            move = [
                                source_base["x"],
                                source_base["y"],
                                best_contested["x"],
                                best_contested["y"],
                                min(available_units, best_contested["units"] + self.min_units_for_contested)
                            ]
                            moves.append(move)
                            self.last_move_time[(source_base["x"], source_base["y"])] = current_time
                            continue
                
                # Regular strategy for non-contested bases
                if not moves:
                    # Sort bases by type priority
                    priority_order = ["SpecialBase", "SpeedyBase", "FortifiedBase", "Base"]
                    neutral_bases.sort(key=lambda b: (
                        priority_order.index(b.get("type", "Base")),
                        self.calculate_base_value(b, game_state)
                    ), reverse=True)
                    
                    for source_base in my_bases:
                        if current_time - self.last_move_time[(source_base["x"], source_base["y"])] < 0.3:
                            continue
                        
                        available_units = max(0, source_base["units"] - self.defensive_threshold)
                        if available_units <= 0:
                            continue
                        
                        # Find best target
                        best_target = None
                        best_value = float('-inf')
                        
                        # Consider both neutral and enemy bases
                        potential_targets = neutral_bases + enemy_bases
                        
                        for target in potential_targets:
                            distance = self.calculate_path_distance(source_base, target, game_state)
                            
                            if distance > self.max_distance:
                                continue
                            
                            # Calculate required units based on unit advantage
                            required_units = target["units"] + 4
                            if unit_advantage >= self.unit_advantage_threshold:
                                required_units = target["units"] + 3  # More aggressive when we have advantage
                            
                            if time_progress > self.aggressive_threshold:
                                required_units = int(required_units * 1.2)
                            
                            if available_units >= required_units:
                                # Calculate target value
                                target_value = self.calculate_base_value(target, game_state)
                                if target["owner"] == 0:  # Neutral bases are more valuable early game
                                    target_value *= (1 - time_progress)
                                else:  # Enemy bases are more valuable late game
                                    target_value *= (1 + time_progress)
                                
                                # Adjust value based on distance
                                target_value /= (distance + 1)
                                
                                if target_value > best_value:
                                    best_value = target_value
                                    best_target = target
                        
                        if best_target:
                            # Create move
                            move = [
                                source_base["x"],
                                source_base["y"],
                                best_target["x"],
                                best_target["y"],
                                min(available_units, best_target["units"] + 4)
                            ]
                            moves.append(move)
                            self.last_move_time[(source_base["x"], source_base["y"])] = current_time
            
            return {"moves": moves}
            
        except Exception as e:
            print(f"Error in make_move: {e}")
            return {"moves": []}  # Return empty moves on error

def main():
    print("🚨 Strategic Player script is running", flush=True)
    if len(sys.argv) < 4:
        print("Usage: python strategic_player2.py <port> <player_id> <player_num>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    player_id = sys.argv[2]
    player_num = int(sys.argv[3])
    
    client = StrategicPlayer(port, player_id, player_num)
    
    if not client.connect():
        sys.exit(1)
    
    client.run()

if __name__ == "__main__":
    main() 