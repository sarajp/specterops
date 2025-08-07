class PlayerState:
    def __init__(self, player):
        self.name = player['name']
        self.role = player['role']
        self.character = player['character']

    def choose_move(self, path):
        pass

    def check_line_of_sight(self):
        pass