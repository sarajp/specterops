roll_d6():
    roll, if 6 recurse and add

setup_game(board_name, agent, hunters):
    load board
    set agent start position
    set car start position
    set escape points (base + extras based on player count)
    set objectives (visible or hidden based on player count)
    set agent hp and equipment count based on player count
    flag traitor rules if 5 players
    return initial GameState

get_legal_moves(state, player):
    for each cell reachable within move_speed:
        exclude walls, structures
        exclude hunter-occupied cells (for agent)
    return list of reachable cells

apply_move(state, player, destination):
    update player position
    check LOS for all hunters against agent new position
    update visible/last_seen flags
    log event

resolve_combat(attacker, target, distance):
    roll_d6, reroll and accumulate on 6
    if roll == 1: miss
    if roll >= distance: hit
    apply wound to target

check_win(state):
    if agent wounds >= 4: hunters win
    if turn > 40: hunters win
    if agent completed 3 objectives and is on escape point: agent wins
    return None if no win yet

end_turn(state, player):
    clear stunned if applicable
    advance turn order
    log state snapshot