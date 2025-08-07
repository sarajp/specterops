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
            self.roads = board['roads']
            self.walls = board['walls']
            self.caches = board['supply_caches']
            self.potential_objectives = board['potential_objectives']
        self.escapes = ['N1', 'A3', 'W3']
        self.objectives = self.set_objectives()

    def build_board(self):
        char_row = []
        current_char_code = ord('A')
        for i in range(0, 23):
            char_row.append(chr(current_char_code))
            current_char_code += 1
        char_grid = [char_row]*32

        num_grid = []
        for i in range(1, 33):
            num_row = [str(i)]*23
            num_grid.append(num_row)

        board_grid = [[char_grid[i][j] + num_grid[i][j] for j in range(23)] for i in range(32)]
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
