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
        player = game_state["player"]
        bases = game_state["bases"]

        my_bases = [b for b in bases if b["owner"] == player]
        neutral_bases = [b for b in bases if b["owner"] == 0]
        enemy_bases = [b for b in bases if b["owner"] != player and b["owner"] != 0]

        def distance(b1, b2):
            return math.sqrt((b1["x"] - b2["x"])**2 + (b1["y"] - b2["y"])**2)

        base_weights = {
            "Base": 2,
            "FortifiedBase": 3,
            "SpecialBase": 4,
            "SpeedyBase": 3
        }

        def target_value(base, my_base, is_enemy=False):
            dist = distance(my_base, base)
            weight = base_weights.get(base["type"], 1)
            unit_cost = base["units"] + 1
            base_score = (weight * 10) / (dist + unit_cost)
            return base_score * (0.5 if is_enemy else 1.0)

        moves = []

        for my_base in my_bases:
            if my_base["units"] < 15:
                continue

            best_target = None
            best_value = -float('inf')

            # اول فقط neutralها رو چک می‌کنیم
            for target in neutral_bases:
                if my_base["units"] > target["units"] *2/3:
                    value = target_value(target, my_base)
                    if value > best_value:
                        best_value = value
                        best_target = target

            # اگر neutral خوب پیدا نشد، بریم سراغ دشمن
            if not best_target:
                for target in enemy_bases:
                    if my_base["units"] > target["units"] * 1.5 + 5:
                        value = target_value(target, my_base, is_enemy=True)
                        if value > best_value:
                            best_value = value
                            best_target = target

            if best_target:
                units_to_send = my_base["units"] // 2
                moves.append([
                    my_base["x"], my_base["y"],
                    best_target["x"], best_target["y"],
                    units_to_send,
                    []
                ])

        return {"moves": moves}



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
