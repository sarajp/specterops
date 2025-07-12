from model.game_model import GameState
from view import GameView

class Controller:
    def __init__(self, root):
        self.model = GameState()
        self.view = GameView(root, self)
        self.current_player = "Agent"