#include <iostream>
#include <string>
#include <vector>
#include <cstring>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>

#ifdef __APPLE__
#include "/opt/homebrew/include/nlohmann/json.hpp"
#else
#include "/usr/include/nlohmann/json.hpp"
#endif

using json = nlohmann::json;
using namespace std;

class GameClient {
public:
    GameClient(int port, const string& playerId, int playerNum)
        : port(port), playerId(playerId), playerNum(playerNum) {}

    bool connect() {
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
        
        if (::connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
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
            ::close(sock);
            sock = -1;
        }
    }
    
    ~GameClient() {
        close();
    }

private:
    int sock = -1;
    int port;
    string playerId;
    int playerNum;
    
    string receiveMessage() {
        char buffer[4096] = {0};
        string result;
        
        while (true) {
            int valread = read(sock, buffer, sizeof(buffer) - 1);
            if (valread <= 0) return "";
            
            result.append(buffer, valread);
            if (strchr(buffer, '\n')) break;
        }
        
        return result;
    }
    
    bool sendMessage(const string& message) {
        return send(sock, message.c_str(), message.length(), 0) != -1;
    }
    
    json makeMove(const json& gameState) {
        // Parse game state
        int player = gameState["player"];
        int size = gameState["size"];
        double gameTime = gameState["game_time"];
        double maxDuration = gameState["game_max_duration"];
        
        auto& bases = gameState["bases"];
        auto& movements = gameState["movements"];
        
        // Example: Find my strongest base and neutral base
        int myStrongestBaseX = -1;
        int myStrongestBaseY = -1;
        int myStrongestUnits = 0;
        
        int neutralBaseX = -1;
        int neutralBaseY = -1;
        int neutralUnits = 0;
        
        for (const auto& base : bases) {
            int owner = base["owner"];
            int units = base["units"];
            int x = base["x"];
            int y = base["y"];
            
            if (owner == player && units > myStrongestUnits) {
                myStrongestBaseX = x;
                myStrongestBaseY = y;
                myStrongestUnits = units;
            } else if (owner == 0 && (neutralBaseX == -1 || units < neutralUnits)) {
                neutralBaseX = x;
                neutralBaseY = y;
                neutralUnits = units;
            }
        }
        
        // Make a move if possible
        json response;
        if (myStrongestBaseX != -1 && neutralBaseX != -1 && myStrongestUnits > 10) {
            json move = {myStrongestBaseX, myStrongestBaseY, neutralBaseX, neutralBaseY, 5};
            response["move"] = move;
        } else {
            // Multi-move example
            json moves = json::array();
            // No moves to make
            response["moves"] = moves;
        }
        
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
