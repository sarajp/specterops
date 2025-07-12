class PlayerState:
    def __init__(self, player, name, pos):
        self.player = player
        self.name = name
        self.position = pos

    def choose_move(self, path):
        pass

    def check_line_of_sight(self):
        pass