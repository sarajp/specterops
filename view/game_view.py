from nicegui import ui, app, events

def display_players():
    ui.label(f'{len(app.storage.general['users'])}/5 players connected.')
    with ui.row():
        ui.label('Agent: ')
        for user in app.storage.general['users']:
            if user['role'] == 1:
                ui.label(user['name'])
    with ui.row():
        ui.label('Hunters: ')
        for user in app.storage.general['users']:
            if user['role'] == 2:
                ui.label(user['name'])
    if len(app.storage.general['users']) > 4:
        ui.label('This game is full!')

class GameView:
    def __init__(self):
        self.render()

    @ui.page('/game_view')
    def render(self):
        ui.page_title('SpecterOps')
        ui.label(f'{len(app.storage.general['users'])}/5 players connected.')
        with ui.row():
            ui.label('Agent: ')
            for user in app.storage.general['users']:
                if user['role'] == 1:
                    ui.label(user['name'])
        with ui.row():
            ui.label('Hunters: ')
            for user in app.storage.general['users']:
                if user['role'] == 2:
                    ui.label(user['name'])
        if len(app.storage.general['users']) > 4:
            ui.label('This game is full!')
        app.add_static_files('/images', './view/assets')
        board_src = '/images/board_sob.png'
        interactive_board = ui.interactive_image(board_src, content='''
            <rect id="N1" x="344" y="17" width="20" height="20" fill="none" stroke="none" pointer-events="all" cursor="pointer" />
            <rect id="K17" x="268" y="415" width="20" height="20" fill="none" stroke="none" pointer-events="all" cursor="pointer" />
        ''').on('svg:pointerdown', lambda e: ui.notify(f'Tile clicked: {e.args['element_id']}'))

        def leave_game(self):
            # for user in app.storage.general['users']:
            #     if user['name'] == 
            print(app.storage.general)

        ui.button('Leave Game', on_click=leave_game)