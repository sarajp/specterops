from nicegui import app, ui
from view.game_view import GameView
from view.join_view import join

app.storage.general.update({'users': []})

@ui.page('/')
def join_view():
    join()    

@ui.page('/game_view')
def setup_game_view():
    GameView().render()

ui.run(dark=True)