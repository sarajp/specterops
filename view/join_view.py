from nicegui import app, ui
import view.game_view
from model.game_model import GameState
from view.game_view import display_players
import json

def join():
    ui.page_title('Join a Game')
    player_count = ui.row()
    display_players(player_count)
    
    def reset_game():
        app.storage.general.update({'users': []})
        ui.navigate.to('/')
        display_players(player_count)

    ui.button('Reset Game', on_click=reset_game)

    player_name = ui.input('Player Name')
    ui.label('Choose your role:')

    role_toggle = ui.toggle(['Agent', 'Hunter'])
    with open('model/resources.json', 'r') as file:
        data = json.load(file)
        agents = data['resources']['agents'].values()
        hunters = data['resources']['hunters'].values()
        agent_names = [item['name'] for item in agents]
        hunter_names = [item['name'] for item in hunters]
    
    def pick_char(role, char):
        player_role = role
        player_character = char
        connect_new_user(player_name.value, player_role, player_character, player_count)

    for role_type in ['Agent', 'Hunter']:
        with ui.card().bind_visibility_from(role_toggle, 'value', value=role_type).tight():
            ui.label(f'{role_type} Picker')
            if role_type == 'Agent':
                chars = agents
            if role_type == 'Hunter':
                chars = hunters
            for char in chars:
                with ui.card_section():
                    ui.button(char['name'], on_click=lambda char=char['name'], r=role_type: pick_char(r, char))
                    ui.label(f'Move speed: {char['move_speed']}')
                    abilities = char['abilities']
                    for ability in abilities:
                        ui.label(f'Ability: {ability}')
    
    #ui.button('Confirm', on_click=lambda: connect_new_user(player_name.value, player_role, player_character, player_count))

    with ui.card():
        app.add_static_files('/images', './view/assets')
        sob_src = '/images/board_sob.png'
        bc_src = '/images/board_bc.webp'
        board_thumbnail = ui.image(sob_src)
        def toggle_image(e):
            if e.value == 'Shadow of Babel':
                board_thumbnail.set_source(sob_src)
            if e.value == 'Broken Covenant':
                board_thumbnail.set_source(bc_src)

        board_toggle = ui.toggle(['Shadow of Babel', 'Broken Covenant'], on_change=toggle_image, value='Shadow of Babel')

    def start_game():
        if len(app.storage.general['users']) < 3:
            ui.notify('Not enough players to start!')
            return
        agent = None
        hunters = []
        for user in app.storage.general['users']:
            if user['role'] == 'Agent':
                agent = user
            else:
                hunters.append(user)
        if not agent:
            ui.notify('No one has the Agent role.')
            return

        def init_game_state():
            app.storage.general.update({'game': GameState(board_toggle.value, agent, hunters)})
            ui.navigate.to('/game_view')

        with ui.dialog() as dialog, ui.card():
            ui.label(f'Start a new {len(app.storage.general['users'])} player game with {agent['name']} as the agent on the {board_toggle.value} board?')
            with ui.row():
                ui.button('Start', on_click=lambda: init_game_state())
                ui.button('Cancel', on_click=dialog.close)
        dialog.open()

    ui.button('Start Game', on_click=start_game)

def connect_new_user(name, role, char, player_count):
    existing_names = []
    existing_chars = []
    agent_claim = ''
    #replace_user = False
    # connected_players = len(app.storage.general['users'])
    # for client in app.clients('/'):
    #     print(client)
    print(name, role, char)

    for user in app.storage.general['users']:
        existing_names.append(user['name'])
        existing_chars.append(user['character'])
        if user['role'] and user['role'] == 'Agent':
            agent_claim = user['name']

    if char in existing_chars:
        ui.notify(f'Someone is already playing as {char}.')
        return
    if char == '':
        ui.notify('Pick a character to play.')
        return
    if name in existing_names:
        ui.notify(f'Someone is already named {name}')
        return
    if name == '':
        ui.notify('Enter a name to display to other players.')
        return
    if role == 'Agent' and agent_claim != '':
        ui.notify(f'{agent_claim} has already taken the Agent role.')
        return
    if role == None:
        ui.notify('Select a role.')
        return
    if len(app.storage.general['users']) > 4:
        ui.label('This game is full!')
        return    
    
    new_user = {'name': name, 'role': role, 'character': char}
    
    # if replace_user:
    #     app.storage.general['users'].update(new_user)
    # else:
    #     app.storage.general['users'].append(new_user)
    app.storage.general['users'].append(new_user)
    view.game_view.display_players(player_count)