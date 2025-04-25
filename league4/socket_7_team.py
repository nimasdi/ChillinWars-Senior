import socket
import json
import sys
import math
import random
import time
import os
from collections import deque



class BehnamAlg:
    def __init__(self):
        self.memory = None
        self.my_states = []

        self.enemy_states = set()
        self.target = set()
        self.indexAttack = 0

        self.startOneRandom = 0
        self.STARTONERANDOMFRAME = 20

    @staticmethod
    def find_bases(bases, player):
        ans = []
        for base in bases:
            if base['owner'] == player:
                ans.append(base)
        return ans
    
    def min_distance(self, bases, player):
        distances = []
        res=None
        mn =1e9
        for base in bases:
            if abs(base['x']-self.my_states[0][0])+abs(base['y']-self.my_states[0][1])==0 : continue
            if abs(base['x']-self.my_states[0][0])+abs(base['y']-self.my_states[0][1])<mn:
                mn=abs(base['x']-self.my_states[0][0])+abs(base['y']-self.my_states[0][1])
                res=base
        
        return {"moves": [
            [self.my_states[0][0], self.my_states[0][1], res['x'], res['y'], 1],
        ]}

    def choose_1(self, game_state, bases, size, player, enemy_player):
        STOP = False

        for i in game_state['movements']:
            if i['owner'] == enemy_player:
                x, y = i['source_x'], i['source_y']
                self.enemy_states.add((x, y))

        if self.memory is None:
            self.memory = {}
            for base in bases:
                if base['owner'] == 0:
                    self.memory[f"{base['x']}-{base['y']}"] = base['units']
                elif base['owner'] == player:
                    self.my_states.append((base['x'], base['y'],))
        else:
            SEE = False
            for base in bases:
                if base['owner'] == 0:
                    if self.memory[f"{base['x']}-{base['y']}"] != base['units']:
                        # return all soldiers at there
                        self.target.add((base['x'], base['y']))
                        SEE = True
                        # return {"moves": [[self.my_states[0][0], self.my_states[0][1], , 100],]}
            if not SEE and len(self.target) == 0:
                self.startOneRandom += 1
                if self.startOneRandom > self.STARTONERANDOMFRAME:
                    # send randomly
                    return self.min_distance(bases, player), STOP     
            
        moves = []
        if len(self.target) == 0:
            self.indexAttack += 1
            if self.indexAttack == 10000: # todo change >>>>>>>>>>>>>>>>>>>>>>>>>>
                enemy_base = BehnamAlg.find_bases(bases, enemy_player)
                self.target.add((enemy_base[0]['x'], enemy_base[0]['y']))
        if len(self.target) != 0:
            target = list(self.target)
            # attack all to the self.target[0]
            my_bases = BehnamAlg.find_bases(bases, player)
            if len(my_bases) >= 2:
                STOP = True

            for i in my_bases:
                moves.append([i['x'], i['y'], target[0][0], target[0][1], 100])
                if target[0][0] == i['x'] and target[0][1] == i['y']:
                    self.target.remove(target[0])

        return {"moves": moves}, STOP


class GameClient:
    def __init__(self, port, player_id, player_num,gamma=0.9, epsilon=1e-6,max_troops =100):
        self.port = int(port)
        self.player_id = player_id
        self.player_num = int(player_num)
        self.sock = None
        self.gamma = gamma  # Discount factor
        self.epsilon = epsilon  # Convergence threshold
        self.max_iterations = 1000
        self.max_troops = max_troops 

        self.startIman = False
        self.startAlg = BehnamAlg()

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(('localhost', self.port))
            print(f"Socket Player {self.player_num} connected to game server on port {self.port}")
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def run(self):
        try:
            while True:
                game_state_str = self.receive_message()
                if not game_state_str:
                    break
                try:
                    game_state = json.loads(game_state_str)
                    move = self.player1_strategy(game_state, self.player_num)
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
        try:
            self.sock.sendall(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def calculate_distance(self, base1, base2):
        """Calculate Manhattan distance between two bases."""
        dx = abs(base1["x"] - base2["x"])
        dy = abs(base1["y"] - base2["y"])
        return dx + dy

    def get_possible_actions(self, game_state, player_num):
        """Generate possible actions for the player."""
        my_bases = [b for b in game_state["bases"] if b["owner"] == player_num]
        enemy_bases = [b for b in game_state["bases"] if b["owner"] == -1]
        neutral_bases = [b for b in game_state["bases"] if b["owner"] == 0]

        actions = []
        
        # Find the base with the least number of troops
        all_bases = enemy_bases + neutral_bases
        target_base = min(all_bases, key=lambda b: b["units"])

        # Consider attacking the base with the least number of troops
        for base in my_bases:
            available_units = base["units"] - 1  # Reserve 1 unit for defense
            if available_units <= 0:
                continue  # Skip if no units are available

            units_to_send = min(available_units, target_base["units"] + 1, self.max_troops)
            
            actions.append({
                "from_base": base,
                "to_base": target_base,
                "units_to_send": units_to_send
            })
        
        return actions

    def get_reward(self, action, game_state):
        """Calculate reward based on the action taken."""
        from_base = action["from_base"]
        to_base = action["to_base"]
        
        # Reward based on the number of troops in the target base
        if to_base["owner"] == 0 and to_base["units"] < action["units_to_send"]:
            return 10 + (1 / (to_base["units"] + 1))  # Higher reward for fewer troops
        elif to_base["owner"] == -1 and to_base["units"] < action["units_to_send"]:
            return 5 + (1 / (to_base["units"] + 1))  # Higher reward for fewer troops
        else:
            return -1  # Failed attack or neutral base with enough units

    def value_iteration(self, game_state, player_num):
        """Perform value iteration to compute the optimal value function and policy."""
        # Initialize value function for each base
        value_function = {}
        for base in game_state["bases"]:
            value_function[(base["x"], base["y"])] = 0  # Initial value is 0
        
        # Iterate until convergence
        for _ in range(self.max_iterations):
            new_value_function = value_function.copy()
            delta = 0
            
            # Iterate over all bases to update values
            for base in game_state["bases"]:
                if base["owner"] != player_num:
                    continue  # Skip non-player bases
                
                current_state = (base["x"], base["y"])
                actions = self.get_possible_actions(game_state, player_num)
                
                max_value = -math.inf
                for action in actions:
                    reward = self.get_reward(action, game_state)
                    next_state = (action["to_base"]["x"], action["to_base"]["y"])
                    future_value = value_function.get(next_state, 0)
                    
                    value = reward + self.gamma * future_value
                    max_value = max(max_value, value)
                
                new_value_function[current_state] = max_value
                delta = max(delta, abs(value_function[current_state] - new_value_function[current_state]))
            
            value_function = new_value_function
            
            # Check for convergence
            if delta < self.epsilon:
                break
        
        return value_function

    def player1_strategy(self, game_state, player_num):
        """Choose moves based on the computed value function."""
        if self.startIman:
            value_function = self.value_iteration(game_state, player_num)
            
            my_bases = [b for b in game_state["bases"] if b["owner"] == player_num]
            moves_to_make = []
            
            # Attack the base with the least number of troops
            all_bases = [b for b in game_state["bases"] if b["owner"] != player_num]
            target_base = min(all_bases, key=lambda b: b["units"])

            # Calculate the total number of units from all bases
            total_units_available = sum(base["units"] - 1 for base in my_bases if base["units"] > 1)  # Reserve 1 unit for defense

            if total_units_available > 0:
                # Send all available units towards the target base
                for base in my_bases:
                    available_units = base["units"] - 1  # Reserve 1 unit for defense
                    if available_units <= 0:
                        continue  # Skip if no units are available

                    units_to_send = min(available_units, total_units_available)
                    moves_to_make.append([
                        base["x"], base["y"],
                        target_base["x"], target_base["y"],
                        units_to_send
                    ])
                    total_units_available -= units_to_send

                    if total_units_available <= 0:
                        break  # All units have been sent

            return {"moves": moves_to_make}
        else:
            player = player_num
        
            # Extract bases from JSON
            bases = game_state["bases"]
            
            # Get my bases, enemy bases and neutral bases
            my_bases = [b for b in bases if b["owner"] == player]
            enemy_player = 2 if player == 1 else 1
            enemy_bases = [b for b in bases if b["owner"] == enemy_player]
            neutral_bases = [b for b in bases if b["owner"] == 0]

            moves, self.startIman = self.startAlg.choose_1(game_state, bases, game_state['size'], player, enemy_player)
            # moves, self.startIman = self.startAlg.choose_1()
            return moves

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
