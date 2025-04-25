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
        Strategic move logic for Mushroom Wars
        """
        player = game_state["player"]
        bases = game_state["bases"]
        movements = game_state["movements"]

        my_bases = [b for b in bases if b["owner"] == player]
        neutral_bases = [b for b in bases if b["owner"] == 0]
        enemy_bases = [b for b in bases if b["owner"] not in (0, player)]

        # Distance helper
        def distance(a, b):
            return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"])**  2)

        moves = []

        my_bases.sort(key=lambda b: b["units"], reverse=True)

        for base in my_bases:
            if base["units"] < 20:
                continue  # Skip weak bases

            # Prioritize special neutral bases (Growth > Speedy > Normal)
            neutral_bases.sort(
                key=lambda b: (b["type"] != "Growth", b["type"] != "Speedy", distance(base, b), b["units"])
            )
            target = None

            for nb in neutral_bases:
                if base["units"] > nb["units"] + 5:
                    target = nb
                    break

            if not target and enemy_bases:
                enemy_bases.sort(key=lambda b: (distance(base, b), b["units"]))
                for eb in enemy_bases:
                    if base["units"] > eb["units"] + 10:
                        target = eb
                        break

            if target:
                units_to_send = min(base["units"] - 5, target["units"] + 10)
                moves.append([
                    base["x"],
                    base["y"],
                    target["x"],
                    target["y"],
                    units_to_send
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
