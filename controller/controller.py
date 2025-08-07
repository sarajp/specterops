from model.game_model import GameState
from view import GameView

class Controller:
    def __init__(self, root):
        self.model = GameState()
        self.view = GameView(root, self)
        self.current_player = "Agent"

    def movement_check(origin, dest):
        o_letter = origin[0]
        o_num = int(origin[1:])
        d_letter = dest[0]
        d_num = int(dest[1:])
        if abs(ord(o_letter)-ord(d_letter))==1 and abs(o_num-d_num)==1:
            return True
        return False