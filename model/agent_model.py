from model.player_model import PlayerState

class AgentState(PlayerState):
    def __init__(self, health, equipment, player):
        super().__init__(player)
        self.health = health
        self.equipment_slots = equipment


