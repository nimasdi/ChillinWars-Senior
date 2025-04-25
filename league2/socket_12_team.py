import socket
import json
import sys
import math
import random
import time
import numpy as np
import sys


class GameClient:
    def __init__(self, port, player_id, player_num):
        self.port = port
        self.player_id = player_id
        self.player_num = player_num
        self.sock = None
        self.d = np.ndarray((100, 100), dtype=float)
        self.first_time = True

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

    def distance(self, base1, base2):
        return math.sqrt((base1["x"] - base2["x"]) ** 2 + (base1["y"] - base2["y"]) ** 2)

    def make_move(self, game_state):
        # print(f"log: {time.time()}", flush=True)\\
        try:
            player = game_state["player"]
            size = game_state["size"]
            game_time = game_state["game_time"]
            max_duration = game_state["game_max_duration"]

            bases = game_state["bases"]
            try:
                w = self.get_w(bases)
            except Exception as e:
                print(e, "fist")
                return None

            try:
                if self.first_time:
                    for i in range(len(bases)):
                        for j in range(len(bases)):
                            self.d[i][j] = self.distance(bases[i], bases[j])
                    self.first_time = False
            except Exception as e:
                print(e, 'stede')
                return None

            my_bases = [b for b in bases if b["owner"] == player]

            actions = self.gen_actions(30, len(bases), len(my_bases), my_bases)

            rewards = self.heuristic(actions, bases, w)

            chosen_action = np.argmax(rewards)
            print(chosen_action)
            chosen_action = actions[chosen_action]
            response = {}
            response["moves"] = []
            try:
                for i in range(len(chosen_action[0])):
                    move = [int(my_bases[i]["x"]), int(my_bases[i]["y"]), int(bases[chosen_action[0][i]]["x"]),
                            int(bases[chosen_action[0][i]]["y"])
                        , chosen_action[1][i].item()]
                    print(move)
                    response["moves"].append(move)
                return response
            except Exception as e:
                print(e, 'f')
                return None
        except Exception as e:
            print(e)
            return None

    def gen_actions(self, number_of_actions, m, n, my_bases):
        actions = []
        base_indices = np.arange(m)  # All possible base indices (0 to m-1)

        for _ in range(number_of_actions):
            # 1. Select n random targets (can include our own bases except sending base)
            targets = np.random.choice(base_indices, size=n, replace=False)

            # 2. For each target, select a random source base that can attack it
            unit_counts = np.zeros(n, dtype=int)

            for i, target in enumerate(targets):
                burst_limit = 20 if my_bases[i]['type'] == 'FortifiedBase' else 10
                max_send = min(my_bases[i]['units'], burst_limit)  # Leave at least 1

                if max_send > 0:
                    # Send random amount between 1 and max_send
                    unit_counts[i] = np.random.randint(0, max_send + 1)

            actions.append((targets, unit_counts))

        return actions

    def get_w(self, bases):
        w = np.ndarray((len(bases),), dtype=float)
        for i in range(len(bases)):
            for j in range(len(bases)):
                w[i] += (2 if bases[i]['type'] != "Base" else 1) / (self.d[i][j] + 1)
        return w

    def heuristic(self, actions, bases, w) -> np.ndarray:
        res = np.ndarray((len(actions),), dtype=float)
        for i, action in enumerate(actions):
            temp = 0
            v = action[0]
            alpha = action[1]

            for i in range(len(v)):
                temp += w[v[i]] * alpha[i] - w[i] * (bases[i]['units'] - alpha[i]) / (
                            self.distance(bases[i], bases[v[i]]) + 1)

            res[i] = temp
        return res


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
