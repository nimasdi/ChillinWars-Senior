import pygame
import random
from enum import Enum
from typing import List, Tuple, Dict, Optional
import math
import time
import heapq
import threading
import concurrent.futures
import json
import socket
import subprocess
import os
import sys
import importlib.util
from uuid import uuid4
import inspect

BASE_MOVEMENT_SPEED = 0.5

FONT_PATH = "megamax-jonathan-too-font/MegamaxJonathanToo-YqOq2.ttf"

CELL_SIZE = 60
MARGIN = 10
COLORS = {
    "neutral": (200, 200, 200),
    "neutral_light": (250, 250, 250),
    "player2": (50, 50, 255),
    "player1": (255, 50, 50),
    "background": (50, 50, 50),
    "text": (255, 255, 255),
    "mushroom_cap_p1": (255, 50, 50),  
    "mushroom_cap_p2": (0, 150, 255),  
    "mushroom_cap_neutral": (150, 150, 150),  
    "mushroom_spots": (255, 255, 255),  
    "mushroom_stem": (255, 250, 220),  
    "speedy_aura": (0, 255, 127, 128),  
    "fortified_aura": (255, 165, 0, 128),  
}

def load_font(size):
    try:
        return pygame.font.Font(FONT_PATH, size)
    except pygame.error:
        return pygame.font.SysFont('Arial', size)

class Player(Enum):
    NEUTRAL = 0
    PLAYER1 = 1
    PLAYER2 = 2

def a_star_search(grid, start, goal):
    """A* pathfinding algorithm to find the shortest path from start to goal."""
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = (current[0] + dx, current[1] + dy)
            if 0 <= neighbor[0] < len(grid) and 0 <= neighbor[1] < len(grid[0]):
                
                if grid[neighbor[1]][neighbor[0]] == 0 or neighbor == goal:
                    tentative_g_score = g_score[current] + 1
                    if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g_score
                        f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))

    print("No path found")
    return []

class TroopMovement:
    def __init__(self, source_x: int, source_y: int, target_x: int, target_y: int, 
                 units: int, owner: Player, duration: float = 1.0, path: List[Tuple[int, int]] = None,
                 speed_multiplier: float = 1.0):
        self.source_x = source_x
        self.source_y = source_y
        self.target_x = target_x
        self.target_y = target_y
        self.units = units
        self.owner = owner
        self.start_time = time.time()
        
        self.duration = duration / speed_multiplier
        self.completed = False
        self.path = path if path else [(source_x, source_y), (target_x, target_y)]
        self.current_path_index = 0
        self.defeated = False  
        self.speed_multiplier = speed_multiplier  
    
    def update(self):
        """Update movement progress and return True if movement is complete"""
        if not self.completed:
            elapsed = time.time() - self.start_time
            if elapsed >= self.duration:
                self.completed = True
                return True
            
            total_path_length = len(self.path) - 1
            if total_path_length == 0:
                self.completed = True
                return True
            segment_duration = self.duration / total_path_length
            self.current_path_index = min(int(elapsed / segment_duration), total_path_length)
        return False
    
    def get_position(self):
        """Get current position of the troop movement"""
        elapsed = time.time() - self.start_time
        progress = min(elapsed / self.duration, 1.0)
        
        total_path_length = len(self.path) - 1
        if total_path_length == 0:
            
            target_pos = self.path[-1]
            target_grid_x = target_pos[0] * (CELL_SIZE + MARGIN) + MARGIN + CELL_SIZE // 2
            target_grid_y = target_pos[1] * (CELL_SIZE + MARGIN) + MARGIN + CELL_SIZE // 2
            return target_grid_x, target_grid_y, progress
        
        segment_duration = self.duration / total_path_length
        segment_index = int(progress * total_path_length)
        segment_progress = (progress * total_path_length) % 1.0
        
        if segment_index >= total_path_length:
            segment_index = total_path_length - 1
            segment_progress = 1.0
        
        start_pos = self.path[segment_index]
        end_pos = self.path[segment_index + 1]
        
        
        start_grid_x = start_pos[0] * (CELL_SIZE + MARGIN) + MARGIN + CELL_SIZE // 2
        start_grid_y = start_pos[1] * (CELL_SIZE + MARGIN) + MARGIN + CELL_SIZE // 2
        end_grid_x = end_pos[0] * (CELL_SIZE + MARGIN) + MARGIN + CELL_SIZE // 2
        end_grid_y = end_pos[1] * (CELL_SIZE + MARGIN) + MARGIN + CELL_SIZE // 2
        
        current_x = start_grid_x + (end_grid_x - start_grid_x) * segment_progress
        current_y = start_grid_y + (end_grid_y - start_grid_y) * segment_progress
        
        return current_x, current_y, progress
    
    def get_radius(self):
        """Get the collision radius of the troop based on its size"""
        return 10 + min(self.units * 0.2, 10)   

class Base:
    def __init__(self, x: int, y: int, owner: Player, units: int):
        self.x = x
        self.y = y
        self.owner = owner
        self.units = units
        self.growth_rate = 1 if owner != Player.NEUTRAL else 0
        self.max_units = 100
        self.last_growth_time = time.time()
        self.growth_interval = 1.0  
        self.cooldown = 0  
    
    def update(self, current_time):
        """Update base units based on real time"""
        if self.owner != Player.NEUTRAL and self.units < self.max_units:
            elapsed = current_time - self.last_growth_time
            if elapsed >= self.growth_interval:
                
                growth_cycles = int(elapsed / self.growth_interval)
                self.units += self.growth_rate * growth_cycles
                self.units = min(self.units, self.max_units)
                
                self.last_growth_time += growth_cycles * self.growth_interval
        
        
        if self.cooldown > 0:
            self.cooldown = max(0, self.cooldown - (current_time - self.last_growth_time))
    
    def process_troop_arrival(self, owner: Player, units: int):
        """Process troops arriving at this base in real-time"""
        
        old_owner = self.owner
        old_units = self.units
        
        if self.owner == Player.NEUTRAL:
            
            if units > self.units:
                self.owner = owner
                self.units = units - self.units
                
                self.growth_rate = 1  
                self.last_growth_time = time.time()  
            else:
                
                self.units -= units
        
        elif self.owner == owner:
            
            self.units += units
            self.units = min(self.units, self.max_units)
        
        else:
            
            if units > self.units:
                self.owner = owner
                self.units = units - self.units
                self.growth_rate = 1  
                self.last_growth_time = time.time()  
            else:
                self.units -= units
    
    def get_speed_multiplier(self) -> float:
        """Return the speed multiplier for troops sent from this base."""
        return 1.0  
    
    def send_troop_multiplier(self) -> float:
        """Return the multiplier for number of troops that can be sent from this base."""
        return 1.0  

class SpecialBase(Base):
    def __init__(self, x: int, y: int, owner: Player, units: int):
        super().__init__(x, y, owner, units)
        self.growth_rate = 2 if owner != Player.NEUTRAL else 0  
    
    def update(self, current_time):
        """Update special base units with 2x growth rate"""
        
        if self.owner != Player.NEUTRAL:
            self.growth_rate = 2
        else:
            self.growth_rate = 0
            
        super().update(current_time)  

class SpeedyBase(Base):
    def __init__(self, x: int, y: int, owner: Player, units: int):
        super().__init__(x, y, owner, units)
        self.growth_rate = 1 if owner != Player.NEUTRAL else 0
    
    def get_speed_multiplier(self) -> float:
        """Return the speed multiplier for troops sent from this base."""
        return 1.5  

class FortifiedBase(Base):
    def __init__(self, x: int, y: int, owner: Player, units: int):
        super().__init__(x, y, owner, units)
        self.growth_rate = 1 if owner != Player.NEUTRAL else 0
    
    def send_troop_multiplier(self) -> float:
        """Return the multiplier for number of troops that can be sent from this base."""
        return 2  

def is_valid_route(grid, route):
    """Check if the specified route is valid (all cells are within bounds and passable)."""
    for x, y in route:
        if not (0 <= x < len(grid) and 0 <= y < len(grid[0])):
            return False
        if grid[y][x] != 0:
            return False
    return True


class GameState:
    def __init__(self, size: int = 8, max_duration: int = 60):
        self.size = size
        self.grid = [[0 for _ in range(size)] for _ in range(size)] 
        self.bases = []
        self.turn = 0  
        self.troop_movements = []  
        self.last_update_time = time.time()
        self.start_time = time.time()  
        self.movement_cooldown = 0.3  
        self.base_cooldowns = {}  
        self.max_duration = max_duration  
        self.initialize_bases()

    def initialize_bases(self):
        
        self.add_base(0, 0, Player.PLAYER1, 50)
        self.add_base(self.size - 1, self.size - 1, Player.PLAYER2, 50)
        
        
        
        num_neutral = random.randint(3, 6)
        for _ in range(num_neutral):
            while True:
                x, y = random.randint(1, self.size - 2), random.randint(1, self.size - 2)
                if self.grid[y][x] == 0:  
                    units = random.randint(10, 40)
                    self.add_base(x, y, Player.NEUTRAL, units)
                    
                    
                    connected = False
                    for base in self.bases:
                        if base.x != x or base.y != y:
                            path = a_star_search(self.grid, (x, y), (base.x, base.y))
                            if path:
                                connected = True
                                break
                    
                    if connected:
                        break
                    else:
                        self.grid[y][x] = 0
                        self.bases.pop()
        

        pos1_x, pos1_y = self.size // 2, self.size // 2
        if self.grid[pos1_y][pos1_x] == 0:  
            self.add_special_base(pos1_x, pos1_y, Player.NEUTRAL, 30)
        else:
            self.place_special_base_at_empty_spot(30)
            
        pos2_x, pos2_y = self.size // 4, self.size // 4 * 3
        if self.grid[pos2_y][pos2_x] == 0:  
            self.add_special_base(pos2_x, pos2_y, Player.NEUTRAL, 30)
        else:
            
            self.place_special_base_at_empty_spot(30)
        
        
        
        sx1, sy1 = self.size // 4, self.size // 4
        if self.grid[sy1][sx1] == 0:  
            self.add_speedy_base(sx1, sy1, Player.NEUTRAL, 25)
        else:
            self.place_speedy_base_at_empty_spot(25)
            
        
        sx2, sy2 = self.size // 4 * 3, self.size // 4 * 3
        if self.grid[sy2][sx2] == 0:  
            self.add_speedy_base(sx2, sy2, Player.NEUTRAL, 25)
        else:
            self.place_speedy_base_at_empty_spot(25)
            
        fx1, fy1 = self.size // 4 * 3, self.size // 4
        if self.grid[fy1][fx1] == 0:  
            self.add_fortified_base(fx1, fy1, Player.NEUTRAL, 35)
        else:
            self.place_fortified_base_at_empty_spot(35)
            
        fx2, fy2 = self.size // 4, self.size // 4 * 3
        if self.grid[fy2][fx2] == 0:  
            self.add_fortified_base(fx2, fy2, Player.NEUTRAL, 35)
        else:
            self.place_fortified_base_at_empty_spot(35)
    
    def place_special_base_at_empty_spot(self, units):
        for x in range(1, self.size - 1):
            for y in range(1, self.size - 1):
                if self.grid[y][x] == 0:
                    self.add_special_base(x, y, Player.NEUTRAL, units)
                    return True
        return False
    
    def place_speedy_base_at_empty_spot(self, units):
        """Helper method to place a speedy base at any available empty spot on the grid"""
        for x in range(1, self.size - 1):
            for y in range(1, self.size - 1):
                if self.grid[y][x] == 0:
                    self.add_speedy_base(x, y, Player.NEUTRAL, units)
                    return True
        return False
    
    def place_fortified_base_at_empty_spot(self, units):
        """Helper method to place a fortified base at any available empty spot on the grid"""
        for x in range(1, self.size - 1):
            for y in range(1, self.size - 1):
                if self.grid[y][x] == 0:
                    self.add_fortified_base(x, y, Player.NEUTRAL, units)
                    return True
        return False
    
    def add_base(self, x: int, y: int, owner: Player, units: int):
        base = Base(x, y, owner, units)
        self.grid[y][x] = base
        self.bases.append(base)
        self.base_cooldowns[(x, y)] = 0  
    
    def add_special_base(self, x: int, y: int, owner: Player, units: int):
        base = SpecialBase(x, y, owner, units)
        self.grid[y][x] = base
        self.bases.append(base)
        self.base_cooldowns[(x, y)] = 0  
    
    def add_speedy_base(self, x: int, y: int, owner: Player, units: int):
        base = SpeedyBase(x, y, owner, units)
        self.grid[y][x] = base
        self.bases.append(base)
        self.base_cooldowns[(x, y)] = 0  
    
    def add_fortified_base(self, x: int, y: int, owner: Player, units: int):
        base = FortifiedBase(x, y, owner, units)
        self.grid[y][x] = base
        self.bases.append(base)
        self.base_cooldowns[(x, y)] = 0  
    
    def get_player_bases(self, player: Player) -> List[Base]:
        return [base for base in self.bases if base.owner == player]
    
    def get_base(self, x: int, y: int) -> Optional[Base]:
        if isinstance(x, int) and isinstance(y, int) and 0 <= x < self.size and 0 <= y < self.size:
            cell = self.grid[y][x]
            if isinstance(cell, Base):
                return cell
        return None
    
    def calculate_distance(self, source_x: int, source_y: int, target_x: int, target_y: int) -> float:
        """Calculate distance between two grid positions"""
        return math.sqrt((target_x - source_x)**2 + (target_y - source_y)**2)
    
    def make_move(self, source_x: int, source_y: int, target_x: int, target_y: int, units: int, player: Player, custom_route: List[Tuple[int, int]] = None):
        """Process a player's move in bursts of 10 units per movement."""
        source_base = self.get_base(source_x, source_y)
        target_base = self.get_base(target_x, target_y)
        current_time = time.time()
        
        
        if not source_base or not target_base:
            return False
            
        
        if source_base.owner != player:
            return False
            
        
        if self.base_cooldowns.get((source_x, source_y), 0) > current_time:
            return False
            
        
        troop_multiplier = source_base.send_troop_multiplier() if hasattr(source_base, 'send_troop_multiplier') else 1.0
        
        
        if units > source_base.units - 1:  
            units = max(0, source_base.units - 1)
            
        if units <= 0:
            return False  
        
        
        source_pos = (source_x, source_y)
        if custom_route and is_valid_route(self.grid, custom_route):
            path = custom_route
        else:
            path = a_star_search(self.grid, source_pos, (target_x, target_y))
            
        if not path:
            return False  
        
        self.base_cooldowns[(source_x, source_y)] = current_time + self.movement_cooldown

        speed_multiplier = source_base.get_speed_multiplier()
        
        
        remaining_units = [units]

        
        def send_bursts():
            while remaining_units[0] > 0:
                
                current_base = self.get_base(source_x, source_y)
                if not current_base or current_base.owner != player:
                    break  
                
                
                burst_units = min(int(10 * troop_multiplier), remaining_units[0])
                burst_units = min(burst_units, current_base.units - 1)  
                
                if burst_units <= 0:
                    break  
                
                
                current_base.units -= burst_units
                remaining_units[0] -= burst_units
                
                
                distance = self.calculate_distance(source_x, source_y, target_x, target_y)
                duration = distance * BASE_MOVEMENT_SPEED
                
                
                self.troop_movements.append(
                    TroopMovement(source_x, source_y, target_x, target_y, burst_units, player, duration, path, speed_multiplier)
                )
                
                print(f"Player {player} sending {burst_units} troops from ({source_x},{source_y}) to ({target_x},{target_y}) at {speed_multiplier}x speed")
                
                time.sleep(1)  

        threading.Thread(target=send_bursts).start()
        return True

    
    def update(self):
        """Update the game state in real-time"""
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        self.last_update_time = current_time
        
        for base in self.bases:
            base.update(current_time)
        
        self.update_troop_movements()
        
        self.turn += 1
    
    def update_troop_movements(self):
        """Update troop movement animations, check for collisions, and process completed movements"""
        completed = []
        defeated = []
        
        
        for movement in self.troop_movements:
            if movement.update():
                
                completed.append(movement)
        
        
        for i, movement1 in enumerate(self.troop_movements):
            if movement1.defeated:
                continue
                
            for j, movement2 in enumerate(self.troop_movements[i+1:], i+1):
                if movement2.defeated:
                    continue
                    
                
                if movement1.owner != movement2.owner:
                    
                    distance = calculate_collision_distance(movement1, movement2)
                    
                    
                    if distance < movement1.get_radius() + movement2.get_radius():
                        
                        winner, loser = resolve_troop_battle(movement1, movement2)
                        
                        
                        if loser and loser.defeated:
                            if loser not in defeated:
                                defeated.append(loser)
                        
                        
                        if movement1.defeated and movement2.defeated:
                            if movement1 not in defeated:
                                defeated.append(movement1)
                            if movement2 not in defeated:
                                defeated.append(movement2)
        
        
        for movement in completed:
            if not movement.defeated:  
                target_base = self.get_base(movement.target_x, movement.target_y)
                if target_base:
                    
                    target_base.process_troop_arrival(movement.owner, movement.units)
        
        
        for movement in completed + defeated:
            if movement in self.troop_movements:
                self.troop_movements.remove(movement)

    def make_multi_move(self, moves_list):
        """Process multiple moves at once
        Args:
            moves_list: List of tuples (source_x, source_y, target_x, target_y, units, player)
        Returns:
            bool: True if at least one move was successful
        """
        success = False
        
        source_units = {}

        
        seen_moves = {}
        for move in moves_list:
            key = (move[0], move[1], move[2], move[3])  
            if key not in seen_moves:
                seen_moves[key] = move
        
        moves_list = list(seen_moves.values())
        

        for source_x, source_y, target_x, target_y, units, player in moves_list:
            source_key = (source_x, source_y)
            if source_key in source_units:
                source_units[source_key] += units
            else:
                source_units[source_key] = units
        
        for source_x, source_y, target_x, target_y, units, player in moves_list:
            source_base = self.get_base(source_x, source_y)
            
            if not source_base or source_base.owner != player:
                continue
            total_units_needed = source_units[(source_x, source_y)]
            if total_units_needed >= source_base.units:
                
                ratio = (source_base.units - 1) / total_units_needed
                adjusted_units = max(1, int(units * ratio))
            else:
                adjusted_units = units
            if self.make_move(source_x, source_y, target_x, target_y, adjusted_units, player):
                success = True
        return success

    def is_game_over(self) -> Optional[Player]:
        """Check if the game is over and return the winner if any"""
        player1_bases = self.get_player_bases(Player.PLAYER1)
        player2_bases = self.get_player_bases(Player.PLAYER2)

        player1_troops_in_transit = sum(movement.units for movement in self.troop_movements if movement.owner == Player.PLAYER1)
        player2_troops_in_transit = sum(movement.units for movement in self.troop_movements if movement.owner == Player.PLAYER2)
        
        if not player1_bases and not player1_troops_in_transit:
            return Player.PLAYER2
        if not player2_bases and not player2_troops_in_transit:
            return Player.PLAYER1
        
        
        if time.time() - self.start_time >= self.max_duration:
            return self.determine_winner_by_units()
        
        return None

    def determine_winner_by_units(self) -> Player:
        """Determine the winner based on the total number of units"""
        player1_units = sum(base.units for base in self.get_player_bases(Player.PLAYER1))
        player2_units = sum(base.units for base in self.get_player_bases(Player.PLAYER2))

        player1_units = 0 if player1_units == None else player1_units
        player2_units = 0 if player2_units == None else player2_units

        player1_troops_in_transit = sum(movement.units for movement in self.troop_movements if movement.owner == Player.PLAYER1)
        player2_troops_in_transit = sum(movement.units for movement in self.troop_movements if movement.owner == Player.PLAYER2)

        player1_troops_in_transit = 0 if player1_troops_in_transit == None else player1_troops_in_transit
        player2_troops_in_transit = 0 if player2_troops_in_transit == None else player2_troops_in_transit
        
        if player1_units + player1_troops_in_transit > player2_units + player2_troops_in_transit:
            return Player.PLAYER1
        elif player2_units + player2_troops_in_transit > player1_units + player1_troops_in_transit:
            return Player.PLAYER2
        else:
            
            return Player.NEUTRAL

def calculate_collision_distance(movement1, movement2):
    """Calculate the distance between two troop movements"""
    x1, y1, _ = movement1.get_position()
    x2, y2, _ = movement2.get_position()
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def resolve_troop_battle(movement1, movement2):
    """Resolve a battle between two troop movements and return the winner"""
    
    
    print("player1 units: ", movement1.units)
    print("player2 units: ", movement2.units)
    if movement1.units > movement2.units:
        movement1.units -= movement2.units
        movement2.defeated = True
        return movement1, movement2
    elif movement2.units > movement1.units:
        movement2.units -= movement1.units
        movement1.defeated = True
        return movement2, movement1
    else:  
        movement1.units = 0  
        movement2.units = 0
        movement1.defeated = True
        movement2.defeated = True
        return None, None
    

IMAGE_CACHE = {}

def load_image(filename):
    """Load an image and cache it for faster reuse"""
    if filename in IMAGE_CACHE:
        return IMAGE_CACHE[filename]
    try:
        image = pygame.image.load(filename)
        IMAGE_CACHE[filename] = image
        return image
    except pygame.error as e:
        print(f"Failed to load image {filename}: {e}")
        return None   

def draw_mushroom(screen, x, y, radius, owner, unit_count, font, cooldown=0):
    """Draw a Mario-style mushroom at the specified position using a PNG image."""
    
    if owner == Player.PLAYER1:
        image_file = "asset/normalRed.png"
    elif owner == Player.PLAYER2:
        image_file = "asset/normalBlue.png"
    else:
        image_file = "asset/normalGray.png"
    
    
    mushroom_image = load_image(image_file)
    
    if mushroom_image:
        
        scaled_size = (radius * 2, radius * 2)
        if (image_file, scaled_size) not in IMAGE_CACHE:
            IMAGE_CACHE[(image_file, scaled_size)] = pygame.transform.scale(mushroom_image, scaled_size)
        
        scaled_image = IMAGE_CACHE[(image_file, scaled_size)]
        screen.blit(scaled_image, (x - radius, y - radius))
    
    text = font.render(str(unit_count), True, COLORS["text"])
    text_rect = text.get_rect(center=(x, y + radius * 0.6))
    
    
    outline_color = (0, 0, 0)
    outline_size = 1
    
    for dx in [-outline_size, outline_size]:
        for dy in [-outline_size, outline_size]:
            outline_rect = text_rect.move(dx, dy)
            outline_text = font.render(str(unit_count), True, outline_color)
            screen.blit(outline_text, outline_rect)
    
    screen.blit(text, text_rect)

    
    if cooldown > 0:
        cooldown_height = radius * 2 * (cooldown / 1.0)
        cooldown_rect = pygame.Rect(
            x - radius,
            y + radius - cooldown_height,
            radius * 2,
            cooldown_height
        )
        cooldown_overlay = pygame.Surface((radius * 2, cooldown_height), pygame.SRCALPHA)
        cooldown_overlay.fill((0, 0, 0, 150))  
        screen.blit(cooldown_overlay, cooldown_rect.topleft)

def draw_speedy_base(screen, x, y, radius, owner, unit_count, font, cooldown=0):
    """Draw a speedy base using a PNG image."""
    
    if owner == Player.PLAYER1:
        image_file = "asset/fireRed.png"
    elif owner == Player.PLAYER2:
        image_file = "asset/fireBlue.png"
    else:
        image_file = "asset/fireGray.png"
    
    
    base_image = load_image(image_file)
    
    if base_image:
        
        scaled_size = (radius * 2, radius * 2)
        if (image_file, scaled_size) not in IMAGE_CACHE:
            IMAGE_CACHE[(image_file, scaled_size)] = pygame.transform.scale(base_image, scaled_size)
        
        scaled_image = IMAGE_CACHE[(image_file, scaled_size)]
        screen.blit(scaled_image, (x - radius, y - radius))
        
        
        aura_color = COLORS["speedy_aura"]
        current_time = time.time()
        ripple_phase = (current_time * 5) % (2 * math.pi)
        ripple_size = radius * 1.3 * (0.9 + 0.1 * math.sin(ripple_phase))
        
        aura_rect = pygame.Rect(
            x - ripple_size, 
            y - ripple_size, 
            ripple_size * 2, 
            ripple_size * 2
        )
        pygame.draw.ellipse(screen, aura_color, aura_rect, width=3)
    
    text = font.render(str(unit_count), True, COLORS["text"])
    text_rect = text.get_rect(center=(x, y + radius * 0.6))
    
    outline_color = (0, 0, 0)
    outline_size = 1
    
    for dx in [-outline_size, outline_size]:
        for dy in [-outline_size, outline_size]:
            outline_rect = text_rect.move(dx, dy)
            outline_text = font.render(str(unit_count), True, outline_color)
            screen.blit(outline_text, outline_rect)
    
    screen.blit(text, text_rect)
    
    
    if cooldown > 0:
        cooldown_height = radius * 2 * (cooldown / 1.0)
        cooldown_rect = pygame.Rect(
            x - radius, 
            y + radius - cooldown_height, 
            radius * 2, 
            cooldown_height
        )
        cooldown_overlay = pygame.Surface((radius * 2, cooldown_height), pygame.SRCALPHA)
        cooldown_overlay.fill((0, 0, 0, 150))
        screen.blit(cooldown_overlay, cooldown_rect.topleft)

def draw_fortified_base(screen, x, y, radius, owner, unit_count, font, cooldown=0):
    """Draw a fortified base using a PNG image."""
    
    if owner == Player.PLAYER1:
        image_file = "asset/bigRed.png"  
    elif owner == Player.PLAYER2:
        image_file = "asset/bigBlue.png"
    else:
        image_file = "asset/bigGray.png"
    
    
    base_image = load_image(image_file)
    
    if base_image:
        
        scaled_size = (radius * 2, radius * 2)
        if (image_file, scaled_size) not in IMAGE_CACHE:
            IMAGE_CACHE[(image_file, scaled_size)] = pygame.transform.scale(base_image, scaled_size)
        
        scaled_image = IMAGE_CACHE[(image_file, scaled_size)]
        screen.blit(scaled_image, (x - radius, y - radius))
        
        
        aura_color = COLORS["fortified_aura"]
        current_time = time.time()
        pulse_phase = (current_time * 2) % (2 * math.pi)
        pulse_size = radius * 1.3 * (0.9 + 0.1 * math.sin(pulse_phase))
        
        
        points = []
        for i in range(6):
            angle = i * (2 * math.pi / 6) + pulse_phase / 3
            px = x + math.cos(angle) * pulse_size
            py = y + math.sin(angle) * pulse_size
            points.append((px, py))
        
        pygame.draw.polygon(screen, aura_color, points, width=3)
    
    
    
    if isinstance(font, pygame.font.Font):
        larger_font = load_font(int(font.get_height() * 1.25))
    else:
        larger_font = pygame.font.SysFont('Arial', int(font.get_height() * 1.25))
    
    text = larger_font.render(str(unit_count), True, COLORS["text"])
    text_rect = text.get_rect(center=(x, y + radius * 0.6))
    
    outline_color = (0, 0, 0)
    outline_size = 1
    
    for dx in [-outline_size, outline_size]:
        for dy in [-outline_size, outline_size]:
            outline_rect = text_rect.move(dx, dy)
            outline_text = larger_font.render(str(unit_count), True, outline_color)
            screen.blit(outline_text, outline_rect)
    
    screen.blit(text, text_rect)
    
    
    if cooldown > 0:
        cooldown_height = radius * 2 * (cooldown / 1.0)
        cooldown_rect = pygame.Rect(
            x - radius, 
            y + radius - cooldown_height, 
            radius * 2, 
            cooldown_height
        )
        cooldown_overlay = pygame.Surface((radius * 2, cooldown_height), pygame.SRCALPHA)
        cooldown_overlay.fill((0, 0, 0, 150))
        screen.blit(cooldown_overlay, cooldown_rect.topleft)


def draw_special_base(screen, x, y, radius, owner, unit_count, font, cooldown=0):
    """Draw a special base using a PNG image."""
    
    if owner == Player.PLAYER1:
        image_file = "asset/twinRed.png"
    elif owner == Player.PLAYER2:
        image_file = "asset/twinBlue.png"
    else:
        image_file = "asset/twinGray.png"
    
    
    base_image = load_image(image_file)
    
    if base_image:
        
        scaled_size = (radius * 2, radius * 2)
        if (image_file, scaled_size) not in IMAGE_CACHE:
            IMAGE_CACHE[(image_file, scaled_size)] = pygame.transform.scale(base_image, scaled_size)
        
        scaled_image = IMAGE_CACHE[(image_file, scaled_size)]
        screen.blit(scaled_image, (x - radius, y - radius))
        
        
        aura_color = (255, 255, 0, 128) 
        aura_radius = radius * 1.5
        aura_rect = pygame.Rect(
            x - aura_radius, 
            y - aura_radius, 
            aura_radius * 2, 
            aura_radius * 2
        )
        pygame.draw.ellipse(screen, aura_color, aura_rect, width=3)
    
    
    
    if isinstance(font, pygame.font.Font):
        larger_font = load_font(int(font.get_height() * 1.25))
    else:
        larger_font = pygame.font.SysFont('Arial', int(font.get_height() * 1.25))
    
    text = larger_font.render(str(unit_count), True, COLORS["text"])
    text_rect = text.get_rect(center=(x, y + radius * 0.6))
    
    outline_color = (0, 0, 0)
    outline_size = 1
    
    for dx in [-outline_size, outline_size]:
        for dy in [-outline_size, outline_size]:
            outline_rect = text_rect.move(dx, dy)
            outline_text = larger_font.render(str(unit_count), True, outline_color)
            screen.blit(outline_text, outline_rect)
    
    screen.blit(text, text_rect)
    
    
    if cooldown > 0:
        cooldown_height = radius * 2 * (cooldown / 1.0)
        cooldown_rect = pygame.Rect(
            x - radius, 
            y + radius - cooldown_height, 
            radius * 2, 
            cooldown_height
        )
        cooldown_overlay = pygame.Surface((radius * 2, cooldown_height), pygame.SRCALPHA)
        cooldown_overlay.fill((0, 0, 0, 150))
        screen.blit(cooldown_overlay, cooldown_rect.topleft)

def are_troops_overlapping(movement1, movement2, threshold=20):
    """Check if two troop movements are overlapping or very close to each other."""
    x1, y1, _ = movement1.get_position()
    x2, y2, _ = movement2.get_position()
    distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    return distance < threshold

def draw_troop_movement(screen, movement, font, overlapping=False, offset=(0, 0)):
    """Draw troops moving between bases using troop_red.png and troop_blue.png images."""
    x, y, progress = movement.get_position()
    
    
    x += offset[0]
    y += offset[1]
    
    
    radius = movement.get_radius()
    
    
    display_radius = radius * 2.0
    
    
    if movement.owner == Player.PLAYER1:
        troop_image_file = "asset/troop_red.png"
        text_color = COLORS["player1"]
    else:
        troop_image_file = "asset/troop_blue.png"
        text_color = COLORS["player2"]
    
    
    troop_image = load_image(troop_image_file)
    
    if troop_image:
        
        scaled_size = (int(display_radius * 2), int(display_radius * 2))
        
        
        if (troop_image_file, scaled_size) not in IMAGE_CACHE:
            scaled_image = pygame.transform.scale(troop_image, scaled_size)
            IMAGE_CACHE[(troop_image_file, scaled_size)] = scaled_image
        else:
            scaled_image = IMAGE_CACHE[(troop_image_file, scaled_size)]
        
        
        screen.blit(scaled_image, (int(x - display_radius), int(y - display_radius)))
    
    
    if isinstance(font, pygame.font.Font):
        larger_font = load_font(int(font.get_height() * 1.25))
    else:
        larger_font = pygame.font.SysFont('Arial', int(font.get_height() * 1.25))
    
    
    unit_text = larger_font.render(str(movement.units), True, text_color)
    
    
    text_rect = unit_text.get_rect(center=(int(x), int(y + display_radius + 10)))
    
    
    outline_color = (0, 0, 0)
    outline_size = 1
    
    for dx in [-outline_size, outline_size]:
        for dy in [-outline_size, outline_size]:
            outline_rect = text_rect.move(dx, dy)
            outline_text = larger_font.render(str(movement.units), True, outline_color)
            screen.blit(outline_text, outline_rect)
    
    screen.blit(unit_text, text_rect)

    
def draw_game(screen, state: GameState):
    """Draw the game UI with enhanced visuals"""
    
    main_font = load_font(20)
    small_font = load_font(16)
    
    
    for y in range(state.size):
        for x in range(state.size):
            pos_x = x * (CELL_SIZE + MARGIN) + MARGIN
            pos_y = y * (CELL_SIZE + MARGIN) + MARGIN
            
            pygame.draw.rect(screen, (100, 100, 100, 50), 
                             (pos_x, pos_y, CELL_SIZE, CELL_SIZE), 1)
    
    
    overlapping_groups = []
    processed_movements = set()
    
    for i, movement1 in enumerate(state.troop_movements):
        if movement1 in processed_movements:
            continue
            
        
        current_group = [movement1]
        processed_movements.add(movement1)
        
        
        for j, movement2 in enumerate(state.troop_movements):
            if movement2 in processed_movements:
                continue
            
            
            for group_movement in current_group:
                if are_troops_overlapping(group_movement, movement2):
                    current_group.append(movement2)
                    processed_movements.add(movement2)
                    break
        
        
        if len(current_group) > 1:
            overlapping_groups.append(current_group)
    
    
    overlapping_movements = set()
    for group in overlapping_groups:
        overlapping_movements.update(group)
    
    for movement in state.troop_movements:
        if movement not in overlapping_movements:
            draw_troop_movement(screen, movement, small_font)
    
    
    for group in overlapping_groups:
        
        group_size = len(group)
        
        
        for i, movement in enumerate(group):
            
            angle = (2 * math.pi * i) / group_size
            
            
            offset_radius = 15  
            offset_x = math.cos(angle) * offset_radius
            offset_y = math.sin(angle) * offset_radius
            
            
            if movement.owner == Player.PLAYER1:
                offset_x *= 1.2  
                offset_y *= 1.2
            
            draw_troop_movement(screen, movement, small_font, True, (offset_x, offset_y))
    
    
    for base in state.bases:
        pos_x = base.x * (CELL_SIZE + MARGIN) + MARGIN + CELL_SIZE // 2
        pos_y = base.y * (CELL_SIZE + MARGIN) + MARGIN + CELL_SIZE // 2
        cooldown = max(0, state.base_cooldowns.get((base.x, base.y), 0) - time.time())

        if isinstance(base, SpecialBase):
            draw_special_base(screen, pos_x, pos_y, CELL_SIZE // 2 - 2, base.owner, base.units, main_font, cooldown)
        elif isinstance(base, SpeedyBase):
            draw_speedy_base(screen, pos_x, pos_y, CELL_SIZE // 2 - 2, base.owner, base.units, main_font, cooldown)
        elif isinstance(base, FortifiedBase):
            draw_fortified_base(screen, pos_x, pos_y, CELL_SIZE // 2 - 2, base.owner, base.units, main_font, cooldown)
        else:
            draw_mushroom(screen, pos_x, pos_y, CELL_SIZE // 2 - 2, base.owner, base.units, main_font, cooldown)
    
    
    info_y = state.size * (CELL_SIZE + MARGIN) + 10
    
    info_surface = pygame.Surface((state.size * (CELL_SIZE + MARGIN), 60), pygame.SRCALPHA)
    info_surface.fill((0, 0, 0, 180))
    screen.blit(info_surface, (0, info_y))
    
    
    game_time = int(time.time() - state.start_time)
    time_text = main_font.render(f"Time: {game_time}s", True, COLORS["text"])
    screen.blit(time_text, (10, info_y + 10))
    
    
    troop_text = main_font.render(f"Active Troops: {len(state.troop_movements)}", True, COLORS["text"])
    screen.blit(troop_text, (200, info_y + 10))
    
    
    p1_bases = state.get_player_bases(Player.PLAYER1)
    p2_bases = state.get_player_bases(Player.PLAYER2)
    p1_units = sum(base.units for base in p1_bases)
    p2_units = sum(base.units for base in p2_bases)
    
    units_text = main_font.render(f"Red: {p1_units} units | Blue: {p2_units} units", True, COLORS["text"])
    screen.blit(units_text, (10, info_y + 30))

def show_game_over(screen, winner, time_up=False):
    """Display a game over message"""
    
    font = load_font(36)
    if time_up:
        time_up_text = "Time is up!"
    else:
        time_up_text = "Game Over!"
    
    if winner == Player.NEUTRAL:
        winner_text = "It's a Draw!"
        winner_color = COLORS["neutral"]
    else:
        winner_text = "Player 1 (Red)" if winner == Player.PLAYER1 else "Player 2 (Blue)"
        winner_color = COLORS["player1"] if winner == Player.PLAYER1 else COLORS["player2"]

    
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    
    
    time_up_render = font.render(time_up_text, True, (255, 255, 255))
    winner_render = font.render(winner_text, True, winner_color)
    
    
    screen_center_x = screen.get_width() // 2
    screen_center_y = screen.get_height() // 2
    
    time_up_rect = time_up_render.get_rect(center=(screen_center_x, screen_center_y - 30))
    winner_rect = winner_render.get_rect(center=(screen_center_x, screen_center_y + 30))
    
    screen.blit(time_up_render, time_up_rect)
    screen.blit(winner_render, winner_rect)
    
    pygame.display.flip()
    time.sleep(3)
    pygame.quit()

class PlayerViewState:
    """A restricted view of the game state for player strategies."""
    def __init__(self, game_state: GameState, player: Player):
        self._game_state = game_state
        self._player = player
        self._move_executed = False  
        
    def get_player_bases(self, player: Player) -> List[Base]:
        """Get a list of bases owned by a player."""
        return self._game_state.get_player_bases(player)
    
    def get_base(self, x: int, y: int) -> Optional[Base]:
        """Get the base at the specified coordinates."""
        return self._game_state.get_base(x, y)
    
    def get_size(self) -> int:
        """Get the grid size."""
        return self._game_state.size
    
    def get_bases(self) -> List[Base]:
        """Get all bases on the map."""
        return self._game_state.bases.copy()
        
    def get_troop_movements(self) -> List[TroopMovement]:
        """Get current troop movements."""
        return [movement for movement in self._game_state.troop_movements 
                if not movement.defeated]
    
    def make_move(self, source_x: int, source_y: int, target_x: int, target_y: int, units: int):
        """Make a move as this player."""
        if self._move_executed:
            print(f"Player {self._player} attempted multiple moves in one turn!")
            return False  
        
        result = self._game_state.make_move(source_x, source_y, target_x, target_y, units, self._player)
        if result:
            self._move_executed = True
        return result
    
    def make_multi_move(self, moves_list):
        """Make multiple moves as this player."""
        if self._move_executed:
            print(f"Player {self._player} attempted multiple multi_moves in one turn!")
            return False  

        player_moves = []
        if isinstance(moves_list, list) and len(moves_list) > 0:
            for move in moves_list:
                if isinstance(move, list) and len(move) == 5:
                    player_moves.append((move[0], move[1], move[2], move[3], move[4], self._player))
            
        result = self._game_state.make_multi_move(player_moves)
        if result:
            self._move_executed = True
        return result
    
    def to_json(self):
        """Convert the player view state to a JSON-serializable dictionary."""
        bases = []
        for base in self._game_state.bases:
            base_type = "Base"
            if isinstance(base, SpecialBase):
                base_type = "SpecialBase"
            elif isinstance(base, SpeedyBase):
                base_type = "SpeedyBase"
            elif isinstance(base, FortifiedBase):
                base_type = "FortifiedBase"
                
            bases.append({
                "x": base.x,
                "y": base.y,
                "owner": base.owner.value,
                "units": base.units,
                "growth_rate": base.growth_rate,
                "type": base_type
            })
            
        movements = []
        for movement in self.get_troop_movements():
            
            current_x, current_y, progress = movement.get_position()
            
            
            grid_x = current_x / (CELL_SIZE + MARGIN)
            grid_y = current_y / (CELL_SIZE + MARGIN)
            
            movements.append({
                "source_x": movement.source_x,
                "source_y": movement.source_y,
                
                
                "units": movement.units,
                "owner": movement.owner.value,
                "current_x": grid_x, 
                "current_y": grid_y, 
                "progress": progress  
            })
            
        return {
            "player": self._player.value,
            "size": self._game_state.size,
            "bases": bases,
            "movements": movements,
            "game_time": time.time() - self._game_state.start_time,
            "game_max_duration": self._game_state.max_duration
        }

class LanguageServer:
    """Server to communicate with external language players."""
    def __init__(self, host='localhost', port=0):
        self.host = host
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        self.port = self.server_socket.getsockname()[1]
        self.connections = {}
        print(f"Language server started on port {self.port}")
        
    def start_player_process(self, language, player_file, player_num):
        """Start a player process in the specified language."""
        player_id = str(uuid4())
        
        if language.lower() == "python":
            
            if os.path.basename(player_file).startswith("socket_") and player_file.endswith(".py"):
                
                cmd = ["python3", player_file, str(self.port), player_id, str(player_num)]
                try:
                    process = subprocess.Popen(cmd)
                    print(f"Started socket-based Python player {player_num} with ID {player_id}")
                    
                    
                    self.server_socket.settimeout(5)
                    try:
                        client_socket, _ = self.server_socket.accept()
                        client_socket.settimeout(None)
                        self.connections[player_id] = client_socket
                        print(f"Player {player_id} connected")
                        return player_id
                    except socket.timeout:
                        print(f"Timeout waiting for player {player_id} to connect")
                        process.kill()
                        return None
                except Exception as e:
                    print(f"Error starting python socket player process: {e}")
                    return None
            else:
                
                try:
                    spec = importlib.util.spec_from_file_location("player_module", player_file)
                    if not spec:
                        print(f"Error: Could not load Python file {player_file}")
                        return None
                        
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    
                    play_func = None
                    possible_names = ["play", f"player{player_num}", "make_move", "strategy"]
                    
                    for name in possible_names:
                        play_func = getattr(module, name, None)
                        if play_func:
                            print(f"Found function '{name}' in {player_file}")
                            break
                    
                    if play_func:
                        
                        def player_wrapper(player_view, player):
                            
                            print(f"Executing as Player {player_num}")
                            
                            try:
                                sig = inspect.signature(play_func)
                                param_count = len(sig.parameters)
                                
                                if param_count == 3:
                                    return play_func(player_view, player, player_num)
                                elif param_count == 2:
                                    return play_func(player_view, player)
                                else:
                                    return play_func(player_view)
                            except Exception as e:
                                print(f"Error calling player function: {e}")
                                return None
                        
                        return player_wrapper
                    else:
                        print(f"Error: No valid function found in {player_file}")
                        print(f"Python players should define one of these functions: {possible_names}")
                        print(f"Example: def play(player_view, player, player_num): ...")
                        return None
                except Exception as e:
                    print(f"Error importing Python module: {e}")
                    return None
        
        
        if language.lower() == "java":
            class_name = os.path.basename(player_file).split('.')[0]
            cmd = ["java", "-cp", os.path.dirname(player_file), class_name, 
                   str(self.port), player_id, str(player_num)]
        elif language.lower() == "cpp":
            executable = os.path.splitext(player_file)[0]
            cmd = [executable, str(self.port), player_id, str(player_num)]
        else:
            print(f"Unsupported language: {language}")
            return None
            
        try:
            process = subprocess.Popen(cmd)
            print(f"Started {language} player {player_num} with ID {player_id}")
            
            
            self.server_socket.settimeout(5)
            try:
                client_socket, _ = self.server_socket.accept()
                client_socket.settimeout(None)
                self.connections[player_id] = client_socket
                print(f"Player {player_id} connected")
                return player_id
            except socket.timeout:
                print(f"Timeout waiting for player {player_id} to connect")
                process.kill()
                return None
        except Exception as e:
            print(f"Error starting player process: {e}")
            return None
    
    def send_game_state(self, player_id, game_state):
        """Send game state to a player process."""
        if isinstance(player_id, str) and player_id in self.connections:
            try:
                client_socket = self.connections[player_id]
                message = json.dumps(game_state) + "\n"
                client_socket.sendall(message.encode())
                
                return True
            except Exception as e:
                print(f"Error sending to player {player_id}: {e}")
                return False
        return True  
    
    def receive_move(self, player_id):
        """Receive a move from a player process."""
        if isinstance(player_id, str) and player_id in self.connections:
            try:
                client_socket = self.connections[player_id]
                client_socket.settimeout(5.0)  
                
                data = b""
                while True:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in chunk:
                        break
                
                client_socket.settimeout(None)  
                
                if data:
                    response_str = data.decode().strip()
                    
                    return json.loads(response_str)
                return None
            except json.JSONDecodeError as e:
                print(f"JSON decode error from player {player_id}: {e}")
                print(f"Received data: {data.decode() if data else 'None'}")
                return None
            except socket.timeout:
                print(f"Timeout waiting for move from player {player_id}")
                return None
            except Exception as e:
                print(f"Error receiving from player {player_id}: {e}")
                return None
        return None
    
    def close(self):
        """Close all connections and the server."""
        for conn in self.connections.values():
            try:
                conn.close()
            except:
                pass
        self.server_socket.close()

def execute_player_strategy(strategy_or_id, game_state, player, language_server=None):
    """Execute a player strategy, which can be a Python function or a player ID for external processes."""
    try:
        player_view = PlayerViewState(game_state, player)
        json_state = player_view.to_json()
        
        if callable(strategy_or_id):  
            
            try:
                
                result = strategy_or_id(json_state, player.value)
                print("GOOOOOOOOOOOOOOOOOOOOOOOOOZ")
                print("NABAYAD IN ETTEFAGH BIOFTE!!")
                print("CALL 911...")
                print("GOOOOOOOOOOOOOOOOOOOOOOOOOZ")
                
                
                if isinstance(result, dict):
                    if "moves" in result:
                        player_view.make_multi_move(result["moves"])
                    elif "move" in result and len(result["move"]) >= 5:
                        m = result["move"]
                        player_view.make_move(m[0], m[1], m[2], m[3], m[4])
            except Exception as e:
                print(f"Error executing Python strategy: {e}")
                import traceback
                traceback.print_exc()
        
        elif language_server and isinstance(strategy_or_id, str):  
            
            success = language_server.send_game_state(strategy_or_id, json_state)
            if not success:
                return
                
            
            move = language_server.receive_move(strategy_or_id)
            if move and "moves" in move:
                player_view.make_multi_move(move["moves"])
            elif move and "move" in move:
                m = move["move"]
                if len(m) >= 5:  
                    player_view.make_move(m[0], m[1], m[2], m[3], m[4])
    except Exception as e:
        print(f"Error in {player} strategy: {e}")
        import traceback
        traceback.print_exc()

def run_game(player1_config=None, player2_config=None, size=8, max_duration=60):
    """
    Run the game with specified player configurations.
    
    player_config format: (language, file_path)
    language can be 'python', 'java', or 'cpp'
    """
    pygame.init()
    
    window_width = size * (CELL_SIZE + MARGIN) + MARGIN
    window_height = window_width + 60  
    
    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Mushroom Wars - RTS")
    
    clock = pygame.time.Clock()
    state = GameState(size, max_duration)
    
    
    state.p1_ready = True
    state.p2_ready = True
    
    
    language_server = LanguageServer()
    
    
    player1_strategy = None
    player2_strategy = None
    
    if player1_config:
        language, file_path = player1_config
        player1_strategy = language_server.start_player_process(language, file_path, 1)
    
    if player2_config:
        language, file_path = player2_config
        player2_strategy = language_server.start_player_process(language, file_path, 2)
    
    
    
    try:
        grass_texture = pygame.image.load("asset/grass_texture.png")
        grass_texture = pygame.transform.scale(grass_texture, (window_width, window_height))
        use_background_image = True
    except pygame.error as e:
        print(f"Failed to load background image: {e}")
        use_background_image = False

    
    running = True
    game_over = False
    winner = None
    font = load_font(16)
    
    
    last_ai_move_time = {
        Player.PLAYER1: time.time(),
        Player.PLAYER2: time.time()
    }
    ai_decision_interval = 1  
    
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    
    while running:
        current_time = time.time()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
        state.update()
        
        winner = state.is_game_over()
        if winner and not game_over:
            game_over = True
            time_up = time.time() - state.start_time >= state.max_duration
            show_game_over(screen, winner, time_up)
            break
        
        if not game_over:
            if current_time - last_ai_move_time[Player.PLAYER2] >= ai_decision_interval:
                executor.submit(execute_player_strategy, player2_strategy, state, Player.PLAYER2, language_server)
                last_ai_move_time[Player.PLAYER2] = current_time
            
            if player1_strategy and current_time - last_ai_move_time[Player.PLAYER1] >= ai_decision_interval:
                executor.submit(execute_player_strategy, player1_strategy, state, Player.PLAYER1, language_server)
                last_ai_move_time[Player.PLAYER1] = current_time
        
        if use_background_image:
            screen.blit(grass_texture, (0, 0))
        else:
            screen.fill(COLORS["background"])
        
        draw_game(screen, state)
        pygame.display.flip()
        clock.tick(60)  
    
    
    executor.shutdown(wait=False)
    language_server.close()
    pygame.quit()

if __name__ == "__main__":
    player1_config = None
    player2_config = None
    size = 8
    max_duration = 60
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--p1" and i + 2 < len(sys.argv):
            player1_config = (sys.argv[i+1], sys.argv[i+2])
            i += 3
        elif sys.argv[i] == "--p2" and i + 2 < len(sys.argv):
            player2_config = (sys.argv[i+1], sys.argv[i+2])
            i += 3
        elif sys.argv[i] == "--size" and i + 1 < len(sys.argv):
            size = int(sys.argv[i+1])
            i += 2
        elif sys.argv[i] == "--duration" and i + 1 < len(sys.argv):
            max_duration = int(sys.argv[i+1])
            i += 2
        else:
            i += 1
    
    run_game(player1_config, player2_config, size, max_duration)
