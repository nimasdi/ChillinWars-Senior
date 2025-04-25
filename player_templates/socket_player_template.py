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
        Implement your strategy here.
        This is a simple example that finds the strongest base and attacks a nearby neutral base.
        """
        # print(f"log: {time.time()}", flush=True)
        player = game_state["player"]
        size = game_state["size"]
        game_time = game_state["game_time"]
        max_duration = game_state["game_max_duration"]
        
        bases = game_state["bases"]
        movements = game_state["movements"]
        
        # Find my strongest base and the nearest neutral base
        my_strongest_base = None
        neutral_target = None
        
        my_bases = [b for b in bases if b["owner"] == player]
        neutral_bases = [b for b in bases if b["owner"] == 0]
        
        # Calculate distance between bases
        def distance(base1, base2):
            return math.sqrt((base1["x"] - base2["x"])**2 + (base1["y"] - base2["y"])**2)
        
        # Find strongest base
        for base in my_bases:
            if not my_strongest_base or base["units"] > my_strongest_base["units"]:
                my_strongest_base = base
        
        # Find closest neutral base
        if my_strongest_base and neutral_bases:
            neutral_bases.sort(key=lambda b: (distance(my_strongest_base, b), b["units"]))
            neutral_target = neutral_bases[0]
        
        # Make a move if possible
        response = {}
        if my_strongest_base and neutral_target and my_strongest_base["units"] > 10:
            # Single move example
            units_to_send = min(my_strongest_base["units"] - 5, neutral_target["units"] + 5)
            move = [
                my_strongest_base["x"], 
                my_strongest_base["y"], 
                neutral_target["x"], 
                neutral_target["y"], 
                units_to_send
            ]
            response["move"] = move
        else:
            # Multi-move example (no moves in this case)
            response["moves"] = []
        
        return response

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
