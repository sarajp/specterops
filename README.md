# Specter Ops

Personal implementation of Specter Ops (Plaid Hat Games) for web-based multiplayer and agent experimentation.

## Running

### Backend

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Runs on `http://localhost:8000`. WebSocket endpoint: `ws://localhost:8000/ws/{player_name}`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173`. The dev server proxies `/ws` to the backend automatically.

### Tests

Backend (pytest):
```bash
pytest
```

Frontend (vitest):
```bash
cd frontend
npm test
```

---

## Rules references

- https://media.plaidhatgames.com/old_images/games/specter-ops-shadow-of-babel/rules.pdf
- https://media.plaidhatgames.com/old_images/games/specter-ops-shadow-of-babel/rules20.pdf
- https://media.plaidhatgames.com/filer_public/f5/81/f581e253-b190-4001-94e1-b6f6e90ceaa9/ph1502-rules_sheet.pdf