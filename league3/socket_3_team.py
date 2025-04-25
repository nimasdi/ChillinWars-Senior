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
    
    def _get_distance(self, x1, y1, x2, y2):
        return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

    def make_move(self, game_state):
        player = game_state["player"]
        enemy_player = 3 - player
        bases = game_state["bases"]

        my_bases = []
        enemy_bases = []
        neutral_bases = []

        for base in bases:
            if base["owner"] == player:
                my_bases.append(base)
            elif base["owner"] == enemy_player:
                enemy_bases.append(base)
            else:
                neutral_bases.append(base)

        available_units = { (b['x'], b['y']): b['units'] for b in my_bases }
        planned_moves = []
        min_garrison = 5

        enemy_bases.sort(key=lambda b: b['units'])
        targeted_enemies = set()

        for enemy_target in enemy_bases:
            target_key = (enemy_target['x'], enemy_target['y'])
            if target_key in targeted_enemies:
                continue

            required_units = enemy_target['units'] + 3

            potential_attackers = []
            for my_base in my_bases:
                my_base_key = (my_base['x'], my_base['y'])
                if available_units[my_base_key] > required_units + min_garrison:
                    dist = self._get_distance(my_base['x'], my_base['y'], enemy_target['x'], enemy_target['y'])
                    potential_attackers.append({'base': my_base, 'dist': dist, 'units_needed': required_units})

            potential_attackers.sort(key=lambda a: a['dist'])

            if potential_attackers:
                attacker_info = potential_attackers[0]
                attacker_base = attacker_info['base']
                attacker_key = (attacker_base['x'], attacker_base['y'])
                units_to_send = attacker_info['units_needed']

                if available_units[attacker_key] >= units_to_send + min_garrison:
                    move = [
                        attacker_base['x'], attacker_base['y'],
                        enemy_target['x'], enemy_target['y'],
                        units_to_send
                    ]
                    planned_moves.append(move)
                    available_units[attacker_key] -= units_to_send
                    targeted_enemies.add(target_key)


        neutral_bases.sort(key=lambda b: b['units'])
        targeted_neutrals = set()

        for neutral_target in neutral_bases:
             target_key = (neutral_target['x'], neutral_target['y'])
             if target_key in targeted_neutrals:
                 continue

             required_units = neutral_target['units'] + 1

             potential_capturers = []
             for my_base in my_bases:
                 my_base_key = (my_base['x'], my_base['y'])
                 if available_units[my_base_key] > required_units + min_garrison:
                     dist = self._get_distance(my_base['x'], my_base['y'], neutral_target['x'], neutral_target['y'])
                     potential_capturers.append({'base': my_base, 'dist': dist, 'units_needed': required_units})

             potential_capturers.sort(key=lambda a: a['dist'])

             if potential_capturers:
                 capturer_info = potential_capturers[0]
                 capturer_base = capturer_info['base']
                 capturer_key = (capturer_base['x'], capturer_base['y'])
                 units_to_send = capturer_info['units_needed']

                 if available_units[capturer_key] >= units_to_send + min_garrison :
                     move = [
                         capturer_base['x'], capturer_base['y'],
                         neutral_target['x'], neutral_target['y'],
                         units_to_send
                     ]
                     planned_moves.append(move)
                     available_units[capturer_key] -= units_to_send
                     targeted_neutrals.add(target_key) 


        my_bases_sorted_strongest = sorted(my_bases, key=lambda b: available_units[(b['x'], b['y'])], reverse=True)
        my_bases_sorted_weakest = sorted(my_bases, key=lambda b: available_units[(b['x'], b['y'])])

        consolidation_threshold = 20

        for strong_base in my_bases_sorted_strongest:
            strong_base_key = (strong_base['x'], strong_base['y'])
            if available_units[strong_base_key] > consolidation_threshold + min_garrison:
                best_reinforce_target = None
                min_dist = float('inf')

                for weak_base in my_bases_sorted_weakest:
                    weak_base_key = (weak_base['x'], weak_base['y'])
                    if strong_base_key == weak_base_key: continue

                    dist = self._get_distance(strong_base['x'], strong_base['y'], weak_base['x'], weak_base['y'])
                    if dist < min_dist and available_units[weak_base_key] < available_units[strong_base_key] / 2 :
                         min_dist = dist
                         best_reinforce_target = weak_base

                if best_reinforce_target:
                     target_key = (best_reinforce_target['x'], best_reinforce_target['y'])
                     units_to_send = int((available_units[strong_base_key] - min_garrison) / 2)

                     if units_to_send > 1:
                        move = [
                            strong_base['x'], strong_base['y'],
                            best_reinforce_target['x'], best_reinforce_target['y'],
                            units_to_send
                        ]
                        planned_moves.append(move)
                        available_units[strong_base_key] -= units_to_send

        return {"moves": planned_moves}




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
