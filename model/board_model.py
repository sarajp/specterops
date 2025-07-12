import json

class BoardState:
    def __init__(self, board_name):
        self.board_grid = self.build_board()
        with open('resources.json', 'r') as file:
            data = json.load(file)
            board = data['resources']['boards'][board_name]
            self.set_roads(board['roads'])
            self.set_walls(board['walls'])
            self.set_supply_caches(board['supply_caches'])

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


    def move_player(self, player, tile):
        pass


    def move_car(self, tile):
        pass


    def add_obstacle(self, obstacle):
        pass


    def remove_obstacle(self, obstacle):
        pass
