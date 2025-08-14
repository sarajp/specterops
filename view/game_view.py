from nicegui import ui, app, events
import json

def display_players(row):
    with row:
        row.clear()
        ui.label(f'{len(app.storage.general['users'])}/5 players connected.')
        ui.label('Agent: ')
        for user in app.storage.general['users']:
            if user['role'] == 'Agent':
                ui.label(f'{user['name']} ({user['character']})')
        ui.label('Hunters: ')
        for user in app.storage.general['users']:
            if user['role'] == 'Hunter':
                ui.label(f'{user['name']} ({user['character']})')
        if len(app.storage.general['users']) > 4:
            ui.label('This game is full!')

class GameView:
    def __init__(self):
        pass

    def tile_to_coords(self, tile, size):
        letter = tile[0]
        num = int(tile[1:])
        x = ((ord(letter)-64)*size)-6
        y = (num*size)+8
        return (x, y)

    def render(self):
        ui.page_title('SpecterOps')
        player_count = ui.row()
        display_players(player_count)
        app.add_static_files('/images', './view/assets')
        if 'game' in app.storage.general.keys():
            board_name = app.storage.general['game'].get_board_state().get_board_name()

            start_x = 195
            start_y = 150
            size = 116

            if board_name == 'Shadow of Babel':
                board_src = '/images/board_sob.png'
                start_x = 14
                start_y = 16
                size = 25
            if board_name == 'Broken Covenant':
                board_src = '/images/board_bc.jpg'
            if board_name == 'Arctic Archives':
                board_src = '/images/board_aa.jpg'

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

            with open('model/resources.json', 'r') as file:
                data = json.load(file)
                if board_name == 'Shadow of Babel':
                    walls = data['resources']['boards']['shadow_of_babel']['walls']
                    potential_objectives = data['resources']['boards']['shadow_of_babel']['potential_objectives']
                if board_name == 'Broken Covenant':
                    walls = data['resources']['boards']['broken_covenant']['walls']
                    potential_objectives = data['resources']['boards']['broken_covenant']['potential_objectives']
                if board_name == 'Arctic Archives':
                    walls = data['resources']['boards']['arctic_archives']['walls']
                    potential_objectives = data['resources']['boards']['arctic_archives']['potential_objectives']
                
                all_potential_objectives = []
                for _, row in potential_objectives.items():
                    for i in row:
                        all_potential_objectives.append(i)

            content = ''
            for i, row in enumerate(board_grid):
                for j, cell in enumerate(row):
                    if cell not in walls:
                        content += f'<rect id="{cell}" x="{(size*j)+start_x}" y="{(size*i)+start_y}" width="{size}" height="{size}" fill="none" stroke="red" pointer-events="all" cursor="pointer" />\n'
                    if cell in all_potential_objectives:
                        content += f'<circle id="potential_objective_{cell}" cx="{(size*j)+26}" cy="{(size*i)+28}" r="{size/2.5}" fill="none" stroke="blue" pointer-events="all" cursor="pointer" />\n'

            agent_start = self.tile_to_coords('N1', size)
            hunter_start = self.tile_to_coords('K23', size)

            agent_mini = f'<text id="agent" x="{agent_start[0]}" y="{agent_start[1]}" fill="purple" pointer-events="all" cursor="pointer">A</text>'
            car_mini = f'<text id="car" x="{hunter_start[0]}" y="{hunter_start[1]}" fill="green" pointer-events="all" cursor="pointer">C</text>'
            hunter_mini_1 = f'<text id="hunter_1" x="{hunter_start[0]}" y="{hunter_start[1]}" fill="green" pointer-events="all" cursor="pointer">H1</text>'
            hunter_mini_2 = f'<text id="hunter_2" x="{hunter_start[0]}" y="{hunter_start[1]}" fill="green" pointer-events="all" cursor="pointer">H2</text>'
            hunter_mini_3 = f'<text id="hunter_3" x="{hunter_start[0]}" y="{hunter_start[1]}" fill="green" pointer-events="all" cursor="pointer">H3</text>'
            hunter_mini_4 = f'<text id="hunter_4" x="{hunter_start[0]}" y="{hunter_start[1]}" fill="green" pointer-events="all" cursor="pointer">H4</text>'

            for mini in [agent_mini, hunter_mini_1, hunter_mini_2, hunter_mini_3, hunter_mini_4, car_mini]:
                content += mini

            interactive_board = ui.interactive_image(board_src, content=content).on('svg:pointerdown', lambda e: ui.notify(f'Tile clicked: {e.args['element_id']}'))# {e.args['image_x']} {e.args['image_y']}'))

        def leave_game():
            # for user in app.storage.general['users']:
            #     if user['name'] == 
            # print(app.storage.general)
            ui.navigate.to('/')

        ui.button('Leave Game', on_click=leave_game)