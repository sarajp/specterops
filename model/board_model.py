import json
import random

class BoardState:
    def __init__(self, board_name):
        self.board_grid = self.build_board()
        self.name = board_name
        with open('model/resources.json', 'r') as file:
            data = json.load(file)
            if board_name == 'Shadow of Babel':
                board = data['resources']['boards']['shadow_of_babel']
            if board_name == 'Broken Covenant':
                board = data['resources']['boards']['broken_covenant'] 
            if board_name == 'Arctic Archives':
                board = data['resources']['boards']['arctic_archives']     
            self.roads = board['roads']
            self.walls = board['walls']
            self.caches = board['supply_caches']
            self.potential_objectives = board['potential_objectives']
        self.escapes = []
        self.objectives = self.set_objectives()
    
    def build_board(self):
        rows = [chr(ord('A') + i) for i in range(23)]
        board_grid = []
        for col in range(1, 33):
            row_entries = []
            for row in rows:
                row_entries.append(row + str(col))
            board_grid.append(row_entries)
        return board_grid
    
    def add_escapes(self, escapes):
        for escape in escapes:
            self.escapes.append(escape)

        
    def set_objectives(self):
        objectives = []
        for i in range(1, 5):
            idx = random.randint(0,5)
            obj = self.potential_objectives[str(i)][idx]
            objectives.append(obj)
            #print(f'Objective {str(i)} at {obj}')
        return objectives


    def move_player(self, player, tile):
        pass


    def move_car(self, tile):
        pass


    def add_obstacle(self, obstacle):
        pass


    def remove_obstacle(self, obstacle):
        pass

    def get_board_name(self):
        return self.name
