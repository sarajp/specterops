# PROJECT CONTEXT — <SpecterOps>

## 1. Goal
-A personal full-stack implementation of Specter Ops (Plaid Hat Games) for playing with friends and experimenting with rule-based and LLM agents.
- MVP: basic rules and gameplay engine, usable for multiple web clients to connect to a session and play the game, storing a simplified log to a file or database
- Future additions: python agents to sub in for players, data analysis to see how different basic strategies combine against each other (prioritize speed, guard exits, recognize other players' strategies)

## 2. Next Steps
- Basic test suite generation ✓
- FastAPI + WebSocket layer ✓
- React frontend board display ✓
- Game logic fixes-- if i try to play the game like i would in meatspace, what still needs support?
- Hunter/agent abilities (deferred stubs in engine)
- Agent item usage
- db.py — SQLite event logging (log_event, fetch_game_log)
- Integration tests via Playwright (see 2b)

## 2a. Deferred UI
- **Legal-move highlighting** — Board.tsx currently allows clicking any cell; adjacency to path tip is enforced in `buildPath` but passable/impassable and hunter-blocked cells are not filtered. Return to this to compute valid next-step cells server-side (or replicate board passability on the client) and visually distinguish/disable non-legal cells.

## 2b. Deferred Testing
- **Board.tsx clickability** — `onCellClick` gating by role/phase is worth testing, but SVG elements aren't accessible by role so tests require `container.querySelector` rather than `screen.getBy*`. Return to this once the board interaction stabilises.
- **Integration tests** — full game flow (lobby → setup → agent turn → hunter turn → win condition) via Playwright once the WebSocket backend is stable.

## 3. Architecture
Frontend:
- React, Typescript, Vite, CSS Modules (chosen over tailwind, zustand, javascript for simplicity, clarity, and personal preference)
Backend:
- Python, FastAPI + websocket
Data:
- SQLite (basic game logs, possible future analysis/training)

## 4. Details
- single game instance, this is for personal use
- prefer minimal dependencies, avoid over-engineering, all code/architecture/logic should be as simple and understandable as possible
- different clients see different amounts of the game state
- frontend centers on image "skins" of the physical game boards, overlaid with svg for interaction
- game states get stored to database for later use
- api should allow input from both a human on another computer or some to-be-created agent
- game_state ground truth stays hidden from hunters, contains board, positions of all players and car, turn number, items used/unused, traitor information
- only the agent may see the agent's position, unless it is in los of a non-traitor hunter
- basic game loop: agent may move and use items at any point during their turn, confirm to end turn. any visible changes are then shown to hunters. hunters agree on an order for their turns, then each take their turn in the agreed order, using abilities at whatever point the ability says. each hunter must also confirm their turn before LOS and ability effects update, and allow the next hunter to go. hunter changes to the game state are visible to everyone. some abilities may persist or retrigger across turns. win state is checked after each player's turn.
- v2 pdf rules override v1. v1 was simply called specter ops, v2 called itself "broken covenant" and called v1 "shadow of babel", and edited some rules, notably the Gun's abilities. an additional board was added afterwards as "arctic archives", using v2 rules and some board specific mechanics

## 5. Project Structure Draft
```
specterops/
├── backend/
│   ├── main.py               # FastAPI app, WebSocket endpoints, startup
│   ├── state.py              # GameState, AgentState, HunterState, VehicleState, BoardData dataclasses
│   ├── engine.py             # setup_game(), apply_move(), get_legal_moves(), resolve_combat(), check_win(), roll_d6()
│   ├── loop.py               # start_turn(), end_turn(), negotiate_hunter_order(), apply_item(), apply_ability(), tick_persistent_effects()
│   ├── visibility.py         # compute_hunter_los(), update_agent_visibility(), is_agent_visible_to(), apply_flashbang_effect(), apply_smoke_effect()
│   ├── board.py              # BoardData dataclass, JSON loader, coordinate helpers, LOS
│   ├── db.py                 # SQLite connection, log_event(), fetch_game_log()
│   └── data/
│       └── resources.json    # board definitions (walls, structures, objectives, escape pts)
│
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx           # WebSocket connection, role-aware state management
│       ├── types/
│       │   ├── game.ts       # mirrors backend dataclasses (GameState, AgentState, etc.)
│       │   └── ws.ts         # WS message union types (inbound/outbound)
│       ├── components/
│       │   ├── Board.tsx
│       │   ├── Lobby.tsx
│       │   ├── SetupView.tsx
│       │   ├── PlayerPanel.tsx
│       │   └── ActionBar.tsx
│       ├── utils/
│       │   └── path.ts       # path building, move speed helpers
│       ├── assets/           # images
│       └── styles/           # CSS Modules per component
│
├── tests/                    # pytest, vite tests, networking, integration
│
├── claude.md
│
└── README.md
```

## 6. Key Rules
 
### Board
- Grid: A–W columns, 1–32 rows, A1 top-left, W32 bottom-right
- Structures are impassable and opaque — any cell not in the coordinate system
- Walls are impassable cells (not edges between cells)
- Barriers are mutable wall cells — added/removed during play, no special pairing logic
- Walls, barriers, and active obstacles (smoke grenades etc.) feed one shared blocker set for LOS
- Roads use the same LOS rules as open cells
### LOS
- Bounding rectangle between two cells; any blocker cell inside (excluding endpoints) blocks LOS
- Same rule applies to degenerate rectangles (same row or column — treated as a line segment)
- Corners block; adjacent cells can be blocked
- LOS checked at end of each hunter's move only, except for last-seen scan (see below)
### Agent
- Moves secretly, up to 4 spaces orthogonally or diagonally per turn; path is tracked including backtracks; total steps capped at move speed
- Cannot move through or onto structures or hunter-occupied spaces
- Becomes visible whenever position is in a hunter's LOS
- Cannot end turn on a vehicle space
- Start position: N1 (Shadow of Babel), M1 (other maps)
- Character identity hidden until first sighting
- Picks items at game start, filtered by availability
- Health tracked on agent state
### Last Seen Token
- Placed when agent passes through any hunter's LOS during a turn but ends outside LOS
- Token placed at the last cell (scanning backward from path end) where agent was in any hunter's LOS
- Agent's character identity remains concealed on the last-seen token until first confirmed sighting
### Objectives
- Completed by ending turn orthogonally or diagonally adjacent to the objective cell
- Completion is tracked privately as pending; becomes public at the start of the agent's next turn
- Agent wins by completing 3 of 4 objectives and reaching an escape point
### Hunter
- Path tracked each turn; spaces moved = len(path) - 1
- LOS check at end of move
- Status effects:
  - **Stunned:** cannot attack or use abilities, movement limited to 2 spaces. Clears at end of that hunter's own turn.
  - **Fatigued**: abilities disabled. Clears when the character moves ≤2 spaces on any turn.
  - **Flashbanged:** vision disabled. Clears at the start of that hunter's own turn.
### Vehicle
- Blocks agent from ending a turn on its space
- Run-over rule (house): when hunters move the vehicle, its full path is published; agent checks own position against every cell in that path in order; agent takes 2 damage per overlap, applied immediately and potentially repeatedly
### Combat
- Roll d6, hit if result ≥ distance in spaces
- Same space = automatic hit
- Roll of 1 = automatic miss regardless of distance
- Roll of 6 = reroll and add to total (repeatable)
### Turn Structure
- Each turn: path → optional ability → optional item → confirm
- Win check after every individual player's turn, including mid-hunter-sequence
### Win Conditions
- **Agent wins:** completes 3 of 4 objectives and reaches an escape point
- **Hunters win:** deal 4 wounds to agent, or agent not escaped by end of round 40
### Player Count Rules
 
| Players | Objectives | Vehicle start | Agent HP | Equipment | Extra escape points |
|---------|-----------|---------------|----------|-----------|-------------------|
| 2–3 | Visible | K17 | 4 | 3 | — |
| 4 | Hidden | K23/K24 | 6 | 5 | A6, W6 |
| 5 | Hidden | K23 | 4 | 3 | A6, W6 + traitor rules |
 
### Escape Points (base)
- Shadow of Babel: A3, N1, W3
- Other maps: A3, M1, W1
### Deferred
- Traitor mechanic (boolean stub on agent state; pending_objectives distinction already supports it)
- Supply cache interactions
- Specific hunter and agent abilities

## 7.  Game Loop 
 
## Setup
- `setup_game()`
- Loop per round (1–40)
---
 
## Agent Turn
- If on supply cache space: agent may draw from supply deck (before moving)
- If on Arctic Archives and adjacent to terminal: agent may place/move up to 3 barriers (before moving)
- Clear agent's flashbang effect if active
- Clear smoke grenade effect if active (start of agent's turn)
- Check objectives:
  - For each incomplete objective, if agent orthogonally/diagonally adjacent → flip token to completed immediately
- Agent moves up to `move_speed`, orthogonal/diagonal
  - Cannot pass through structures or hunter-occupied spaces
  - Cannot end on vehicle space
  - Stopped at space before any hunter's space if path would enter it
  - Track full path including backtracks
- Agent optionally uses one item before or after moving
- Compute last-seen token:
  - Scan path backward from end
  - Find last cell inside any hunter's LOS (accounting for active smoke/flashbang blockers)
  - If found AND agent ends outside all LOS → place/update last-seen token there
  - If agent ends inside LOS → place visible marker instead
- Agent confirms turn
- Tick persistent effects owned by agent
- `check_win()`:
  - Agent wins if 3+ objectives complete AND on escape point AND no hunter on that escape point
  - Hunters win if round == 40 and agent has not escaped
---
 
## Hunter Turns
- Hunters negotiate turn order (once per round)
- Track vehicle move budget for this round (shared across all hunters, capped at vehicle's move value)
- For each hunter in agreed order:
  - Clear this hunter's flashbang effect if active
  - If adjacent to terminal (Arctic Archives): may place/move up to 3 barriers; may also remove any number of barriers
  - Hunter moves up to `move_speed` OR uses vehicle:
    - If hunter starts turn in vehicle, may move vehicle instead (road-only, orthogonal/diagonal)
    - Vehicle move deducts from shared round budget
    - Entering/exiting vehicle ends movement for that turn
    - Hunter may exit then attack on same turn
    - Hunter in vehicle cannot attack
    - Hunter cannot be stunned while in vehicle
    - **TODO: vehicle interaction with agent space — revisit**
  - Hunter optionally uses one or more abilities at timing specified by each ability (disabled if stunned or fatigued)
  - Hunter confirms turn
  - Compute LOS for this hunter (checked at end of move):
    - Smoke grenade token blocks LOS if active (does not block movement)
    - If agent in LOS → place visible marker, reveal position to all hunters
    - If first sighting → reveal agent identity
  - If agent visible: hunter may attempt attack at any distance
    - Roll d6; hit if result ≥ distance (same space = auto hit, though co-location cannot occur in normal play)
    - Roll of 1 = auto miss
    - Roll of 6 = reroll and add (repeatable)
    - On hit → agent loses 1 health
  - Tick persistent effects owned by this hunter
  - Clear status effects at end of turn:
    - Stunned → clears (cannot attack or use abilities this turn; movement capped at 2)
    - Fatigued → clears if moved ≤ 2 spaces this turn (abilities disabled while active)
  - `check_win()`:
    - Hunters win if agent health ≤ 0
    - Agent wins if 3+ objectives complete AND on escape point AND no hunter on that escape point
- Increment round