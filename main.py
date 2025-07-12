from nicegui import app, ui
from uuid import uuid4
import json

def display_players():
    with ui.row():
        ui.label(f'{len(app.storage.general['users'])}/5 players connected.')
        ui.label('Agent: ')
        for user in app.storage.general['users']:
            if user['role'] == 1:
                ui.label(user['name'])
        ui.label('Hunters: ')
        for user in app.storage.general['users']:
            if user['role'] == 2:
                ui.label(user['name'])
        if len(app.storage.general['users']) > 4:
            ui.label('This game is full!')


@ui.page('/')
def join_view():
    ui.page_title('Join a Game')
    user_id = str(uuid4())

    
    def reset_game():
        app.storage.general.update({'users': []})
        ui.navigate.to('/')

    
    ui.button('Reset Game', on_click=reset_game)
    display_players()

    player_name = ui.input('Player Name')
    ui.label('Choose your role:')
    player_role = ui.radio({1: 'Agent', 2: 'Hunter'}).props('inline')

    
    def link_to_game():
        connected_players = len(app.storage.general['users'])
        
        existing_names = []
        agent_claim = ''
        for user in app.storage.general['users']:
            if user['name']:
                existing_names.append(user['name'])
            if user['role'] and user['role'] == 1:
                agent_claim = user['name']

        if player_name.value in existing_names:
            ui.notify('Someone is already using that name.')
            return
        if player_name.value == "":
            ui.notify('Enter a name to display to other players.')
            return
        if player_role.value == 1 and agent_claim != '':
            ui.notify(f'{agent_claim} has already taken the Agent role.')
            return
        if player_role.value == None:
            ui.notify('Select a role.')
            return
        if len(app.storage.general['users']) > 4:
            ui.label('This game is full!')
            return
        new_user = {'id': user_id, 'name': player_name.value, 'role': player_role.value}
        app.storage.general['users'].append(new_user)
        print(new_user)
        ui.navigate.to('/game_view')

    ui.button('Confirm', on_click=link_to_game)



@ui.page('/game_view')
def game_view():
    ui.page_title('SpecterOps')
    display_players()
    app.add_static_files('/images', './view/assets')
    board_src = '/images/board_sob.png'

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
        walls = data['resources']['boards']['shadow_of_babel']['walls']
        potential_objectives = data['resources']['boards']['shadow_of_babel']['potential_objectives']
        all_potential_objectives = []
        for _, row in potential_objectives.items():
            for i in row:
                all_potential_objectives.append(i)

    content = ''
    start_x = 14
    start_y = 16
    size = 25
    for i, row in enumerate(board_grid):
        for j, cell in enumerate(row):
            if cell not in walls:
                content += f'<rect id="{cell}" x="{(size*j)+start_x}" y="{(size*i)+start_y}" width="{size}" height="{size}" fill="none" stroke="red" pointer-events="all" cursor="pointer" />\n'
            if cell in all_potential_objectives:
                content += f'<circle id="{cell}" cx="{(size*j)+26}" cy="{(size*i)+28}" r="{size/2.5}" fill="none" stroke="blue" pointer-events="all" cursor="pointer" />\n'

    interactive_board = ui.interactive_image(board_src, content=content).on('svg:pointerdown', lambda e: ui.notify(f'Tile clicked: {e.args['element_id']}'))

    def leave_game():
        # for user in app.storage.general['users']:
        #     if user['name'] == 
        print(app.storage.general)

    ui.button('Leave Game', on_click=leave_game)

ui.run(dark=True)