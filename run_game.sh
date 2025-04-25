#!/bin/bash

if [ $1 == "cpp" ]; then
    # Compile the C++ player
    echo "Compiling C++ player..."
    g++ -std=c++17 ./player_templates/CppPlayer.cpp -o ./player_templates/CppPlayer -I/opt/homebrew/include

    # Check if compilation was successful
    if [ $? -ne 0 ]; then
        echo "C++ compilation failed."
        exit 1
    fi
fi

# Run the game with both players
# Note that socket_player1.py is now recognized as a socket-based player
python rts_game.py --p1 python league4/socket_7_team.py --p2 python league3/socket_1_team.py --size 11 --duration 360
