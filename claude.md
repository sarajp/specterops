# PROJECT CONTEXT — <SpecterOps>

## 1. Goal
-A personal full-stack implementation of Specter Ops (Plaid Hat Games) for playing with friends and experimenting with rule-based and LLM agents.
- MVP: basic rules and gameplay engine, usable for multiple web clients to connect to a session and play the game, storing a simplified log to a file or database
- Future additions: python agents to sub in for players, data analysis to see how different basic strategies combine against each other (prioritize speed, guard exits, recognize other players' strategies)

## 2. Next Steps
- plan intermediate steps such as
- basic test suite generation
- FastAPI + WebSocket layer
- React frontend board display

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

## 5. Project Structure Draft
```
specterops/
├── backend/
│   ├── main.py               # FastAPI app, WebSocket endpoints, startup
│   ├── engine.py             # setup_game(), apply_move(), legal move generation, win check
│   ├── state.py              # GameState, AgentState, HunterState, VehicleState dataclasses
│   ├── board.py              # BoardData dataclass, JSON loader, coordinate helpers, LOS
│   ├── views.py              # filter_state_for_role(state, role) → partial GameState
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
│       │   ├── Cell.tsx
│       │   ├── PlayerPanel.tsx
│       │   └── ActionBar.tsx
│       └── styles/           # CSS Modules per component
│
├── tests/
│   ├── test_board.py
│   ├── test_engine.py
│   └── test_state.py
│
└── README.md
```

## 6. Key rules (PDF summary)
### Board
- Grid: A–W columns, 1–32 rows, A1 top-left, W32 bottom-right
- Structures are impassable and opaque — any cell not in the coordinate system
- Walls are blocked cells (not edges between cells)
- Barriers are temporary wall pairs — block LOS through either cell in the pair
- Active obstacles (smoke grenades etc.) feed the same blocker set as walls
### Agent
- Moves secretly on movement sheet, up to 4 spaces orthogonally or diagonally
- Cannot move through or onto structures or hunter-occupied spaces
- Start position: N1 (Shadow of Babel), M1 (other maps)
- Visible = ends move in LOS of a hunter
- Last seen = passed through LOS but ended outside it
### Hunter
- LOS: infinite down current row and column, blocked by walls
- On a road space: additional LOS down the road stretch
- LOS check only happens at the end of a hunter's move
### LOS heuristic
Draw the axis-aligned bounding rectangle between two cells. If any wall, barrier, or obstacle cell falls inside that rectangle (excluding the two endpoint cells themselves), LOS is blocked.
- Corners block
- Adjacent cells can be blocked
- Same rule applies to degenerate rectangles (same row or column — treated as a line segment)
### Combat
- Roll d6, hit if result ≥ distance in spaces
- Same space = automatic hit
- Roll of 1 = automatic miss regardless of distance
- Roll of 6 = reroll and add to total (repeatable)
### Win conditions
- **Agent wins:** completes 3 of 4 objectives and reaches an escape point
- **Hunters win:** deal 4 wounds to the agent, or agent fails to escape by end of round 40
### Player count rules
 
| Players | Objectives | Vehicle start | Agent HP | Equipment | Extra escape points |
|---------|-----------|---------------|----------|-----------|-------------------|
| 2–3 | Visible | K17 | 4 | 3 | — |
| 4 | Hidden | K23/K24 | 6 | 5 | A6, W6 |
| 5 | Hidden | K23 | 4 | 3 | A6, W6 + traitor rules |
 
### Escape points (base)
- Shadow of Babel: A3, N1, W3
- Other maps: A3, M1, W1
### Status effects
- **Stunned:** cannot attack or use abilities, movement limited to 2 spaces. Clears at end of that hunter's turn.
- **Fatigued** (v2 only): abilities disabled. Clears when the character moves ≤2 spaces on any turn.
---
 