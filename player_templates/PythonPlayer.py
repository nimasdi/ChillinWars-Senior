import socket
import json
import time
import math

class GameClient:
    def __init__(self, port, player_id, player_num):
        self.port = port
        self.player_id = player_id
        self.player_num = player_num
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("localhost", self.port))
        print(f"Connected to game server on port {self.port}")

    def send_message(self, message):
        self.sock.sendall((message + "\n").encode())

    def receive_message(self):
        data = b""
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in chunk:
                break
        return data.decode().strip()

    def make_move(self, game_state):
        # Parse game state
        player = game_state["player"]
        bases = game_state["bases"]

        # Find my strongest base and a neutral base
        my_strongest_base = None
        neutral_base = None

        for base in bases:
            if base["owner"] == player:
                if not my_strongest_base or base["units"] > my_strongest_base["units"]:
                    my_strongest_base = base
            elif base["owner"] == 0:  # Neutral base
                if not neutral_base or base["units"] < neutral_base["units"]:
                    neutral_base = base

        # Make a move if possible
        if my_strongest_base and neutral_base and my_strongest_base["units"] > 10:
            # Format the move as expected by the game server
            move = [
                my_strongest_base["x"],
                my_strongest_base["y"],
                neutral_base["x"],
                neutral_base["y"],
                int(my_strongest_base["units"] / 2)  # Send half of our units
            ]
            print(f"Making move: {move}")
            return {"move": move}
        else:
            print("No valid move found")
            # Important: Return empty array for move, not empty moves dictionary
            return {"move": []}

    def run(self):
        while True:
            try:
                game_state_str = self.receive_message()
                if not game_state_str:
                    print("Empty game state received, exiting")
                    break

                game_state = json.loads(game_state_str)
                print(f"Received game state: player={game_state['player']}, bases={len(game_state['bases'])}")
                
                move = self.make_move(game_state)
                move_str = json.dumps(move)
                print(f"Sending move: {move_str}")
                self.send_message(move_str)
            except Exception as e:
                print(f"Error in game loop: {e}")
                break

    def close(self):
        if self.sock:
            self.sock.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: PythonPlayer.py <port> <player_id> <player_num>")
        sys.exit(1)

    port = int(sys.argv[1])
    player_id = sys.argv[2]
    player_num = int(sys.argv[3])

    print(f"Starting player {player_num} with ID {player_id} on port {port}")

    client = GameClient(port, player_id, player_num)
    try:
        client.connect()
        client.run()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
