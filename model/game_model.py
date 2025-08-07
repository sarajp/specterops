from model.agent_model import AgentState
from model.hunter_model import HunterState
from model.board_model import BoardState
import json
import random

def roll_d6():
    return random.randint(1,6)

class GameState:
    def __init__(self, board, agent, hunters):
        self.turn_count = 0
        self.board_state = BoardState(board)
        self.players = [agent] + hunters
        self.agent = AgentState(4, 3, agent)
        self.hunters = []
        for hunter in hunters:
            self.hunters.append(HunterState(hunter))
        self.board_state.add_escapes(['A3', 'M1', 'W1'])

        if len(hunters) < 3:
            self.car_start = 'K17'
            self.objective_visible = True
        else:
            self.car_start = 'K23'
            self.objective_visible = False
            self.board_state.add_escapes(['A6', 'W6'])
            if len(hunters) > 3:
                self.agent = AgentState(6, 5, agent)

        # 2-3 player car starts on k17, public objectives, 4 health, 3 equipment, escape points A3, M1, W1
        # 4 player starts on k23, secret objectives, 6 health, 5 equipment, escape points A3, M1, W1, A6, W6
        # 5 player starts on k23, secret objectives, 4 health, 3 equipment, escape points A3, M1, W1, A6, W6, TRAITOR RULES

    def get_turn_count(self):
        return self.turn_count
    
    def get_board_state(self):
        return self.board_state
    
    def get_players(self):
        return self.players
    
    def get_objectives(self):
        return self.objective_visible

