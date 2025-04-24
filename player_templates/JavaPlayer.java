import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.Socket;
import java.util.*;
import org.json.JSONArray;
import org.json.JSONObject;

public class JavaPlayer {
    private static Socket socket;
    private static BufferedReader in;
    private static PrintWriter out;
    private static int playerNum;
    
    public static void main(String[] args) {
        if (args.length < 3) {
            System.err.println("Usage: JavaPlayer <port> <player_id> <player_num>");
            System.exit(1);
        }
        
        int port = Integer.parseInt(args[0]);
        String playerId = args[1];
        playerNum = Integer.parseInt(args[2]);
        
        try {
            // Connect to the game server
            socket = new Socket("localhost", port);
            in = new BufferedReader(new InputStreamReader(socket.getInputStream()));
            out = new PrintWriter(socket.getOutputStream(), true);
            
            System.out.println("Connected to game server on port " + port);
            
            // Game loop
            String gameStateJson;
            while ((gameStateJson = in.readLine()) != null) {
                JSONObject gameState = new JSONObject(gameStateJson);
                JSONObject move = makeMove(gameState);
                out.println(move.toString());
            }
            
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            try {
                if (socket != null) socket.close();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }
    
    private static JSONObject makeMove(JSONObject gameState) {
        // Parse game state
        int player = gameState.getInt("player");
        int size = gameState.getInt("size");
        double gameTime = gameState.getDouble("game_time");
        double maxDuration = gameState.getDouble("game_max_duration");
        
        JSONArray basesJson = gameState.getJSONArray("bases");
        JSONArray movementsJson = gameState.getJSONArray("movements");
        
        // Example: Find my strongest base and neutral base
        int myStrongestBaseX = -1;
        int myStrongestBaseY = -1;
        int myStrongestUnits = 0;
        
        int neutralBaseX = -1;
        int neutralBaseY = -1;
        int neutralUnits = 0;
        
        for (int i = 0; i < basesJson.length(); i++) {
            JSONObject base = basesJson.getJSONObject(i);
            int owner = base.getInt("owner");
            int units = base.getInt("units");
            int x = base.getInt("x");
            int y = base.getInt("y");
            
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
        JSONObject response = new JSONObject();
        if (myStrongestBaseX != -1 && neutralBaseX != -1 && myStrongestUnits > 10) {
            JSONArray move = new JSONArray();
            move.put(myStrongestBaseX);
            move.put(myStrongestBaseY);
            move.put(neutralBaseX);
            move.put(neutralBaseY);
            move.put(5);  // send 5 units
            
            response.put("move", move);
        } else {
            // Multi-move example
            JSONArray moves = new JSONArray();
            // No moves to make
            response.put("moves", moves);
        }
        
        return response;
    }
}
