import json

class GameState:
    def __init__(self, board, players, vehicle):
        self.board_state = board
        self.players = players
        self.vehicle = vehicle
        self.turn_count = 0

        # 2-3 player car starts on k17, public objectives, 4 health, 3 equipment, escape points A3, M1, W1
        # 4 player starts on k24, secret objectives, 6 health, 5 equipment, escape points A3, M1, W1, A6, W6
        # 5 player starts on k24, secret objectives, 4 health, 3 equipment, escape points A3, M1, W1, A6, W6, TRAITOR RULES