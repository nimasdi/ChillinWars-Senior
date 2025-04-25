#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#endif

#include <algorithm>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <cstring>

#include "json.hpp"

using json = nlohmann::json;
using namespace std;

struct Base {
  int growth_rate;
  int owner;
  string type;
  int units;
  int x;
  int y;

  NLOHMANN_DEFINE_TYPE_INTRUSIVE(Base, growth_rate, owner, type, units, x, y)
};

struct Movement {
  float current_x;
  float current_y;
  int owner;
  float progress;
  float source_x;
  float source_y;
  int units;

  NLOHMANN_DEFINE_TYPE_INTRUSIVE(Movement, current_x, current_y, owner, progress, source_x, source_y, units)
};

class GameClient {
public:
  GameClient(int port, const string& playerId, int playerNum)
      : port(port), playerId(playerId), playerNum(playerNum) {}

  bool connect() {
#ifdef _WIN32
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
      cerr << "WSAStartup failed" << endl;
      return false;
    }
#endif

    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
      cerr << "Socket creation error" << endl;
      return false;
    }

    struct sockaddr_in serv_addr;
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(port);

    if (inet_pton(AF_INET, "127.0.0.1", &serv_addr.sin_addr) <= 0) {
      cerr << "Invalid address" << endl;
      return false;
    }

    if (::connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
      cerr << "Connection failed" << endl;
      return false;
    }

    cout << "Connected to game server on port " << port << endl;
    return true;
  }

  bool run() {
    while (true) {
      string gameStateStr = receiveMessage();
      if (gameStateStr.empty()) break;

      try {
        json gameState = json::parse(gameStateStr);
        json move = makeMove(gameState);

        string moveStr = move.dump();
        sendMessage(moveStr + "\n");
      } catch (json::exception& e) {
        cerr << "JSON error: " << e.what() << endl;
        break;
      }
    }
    return true;
  }

  void close() {
    if (sock >= 0) {
#ifdef _WIN32
      closesocket(sock);
      WSACleanup();
#else
      ::close(sock);
#endif
      sock = -1;
    }
  }

  ~GameClient() {
    close();
  }

private:
#ifdef _WIN32
  SOCKET sock = INVALID_SOCKET;
#else
  int sock = -1;
#endif
  int port;
  string playerId;
  int playerNum;

  string receiveMessage() {
    char buffer[4096] = {0};
    string result;

    while (true) {
#ifdef _WIN32
      int valread = recv(sock, buffer, sizeof(buffer) - 1, 0);
#else
      int valread = read(sock, buffer, sizeof(buffer) - 1);
#endif
      if (valread <= 0) return "";

      result.append(buffer, valread);
      if (strchr(buffer, '\n')) break;
    }

    return result;
  }

  bool sendMessage(const string& message) {
    return send(sock, message.c_str(), static_cast<int>(message.length()), 0) != -1;
  }

  json makeMove(const json& gameState) {
    int player = gameState["player"];
    int size = gameState["size"];
    double gameTime = gameState["game_time"];
    double maxDuration = gameState["game_max_duration"];

    vector<Base> bases = gameState["bases"].get<vector<Base>>();
    vector<Movement> movements = gameState["movements"].get<vector<Movement>>();

    vector<Base> myBases;
    copy_if(bases.begin(), bases.end(), back_inserter(myBases), [player](const Base& base) {
      return base.owner == player;
    });

    vector<Base> neutralBases;
    copy_if(bases.begin(), bases.end(), back_inserter(neutralBases), [](const Base& base) {
      return base.owner == 0;
    });

    vector<Base> enemyBases;
    copy_if(bases.begin(), bases.end(), back_inserter(enemyBases), [player](const Base& base) {
      return base.owner != player && base.owner != 0;
    });

    json response;
    json moves = json::array();

    if (!myBases.empty() && !neutralBases.empty()) {
      moves.push_back({myBases[0].x, myBases[0].y, neutralBases[0].x, neutralBases[0].y, 5});
    }

    response["moves"] = moves;
    return response;
  }
};

int main(int argc, char* argv[]) {
  if (argc < 4) {
    cerr << "Usage: CppPlayer <port> <player_id> <player_num>" << endl;
    return 1;
  }

  int port = stoi(argv[1]);
  string playerId = argv[2];
  int playerNum = stoi(argv[3]);

  GameClient client(port, playerId, playerNum);

  if (!client.connect()) {
    return 1;
  }

  client.run();
  client.close();

  return 0;
}

