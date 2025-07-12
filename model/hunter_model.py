from player_model import PlayerState

class HunterState(PlayerState):
    def __init__(self, player, name):
        self.player = player
        self.name = name