from player_model import PlayerState

class AgentState(PlayerState):
    def __init__(self, player, name):
        self.player = player
        self.name = name


