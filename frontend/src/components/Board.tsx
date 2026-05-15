import { useState } from 'react';
import type { GameView } from '../types/game';
import boardSob from '../assets/board_sob.png';
import boardBc from '../assets/board_bc.jpg';
import boardAa from '../assets/board_aa.jpg';
import styles from '../styles/Board.module.css';

// Grid calibration per board. Only Shadow of Babel is confirmed; others TBD.
const BOARD_CONFIGS: Record<string, { startX: number; startY: number; cellSize: number }> = {
  'Shadow of Babel':  { startX: 14, startY: 16, cellSize: 25 },
  'Broken Covenant':  { startX: 14, startY: 16, cellSize: 25 },
  'Arctic Archives':  { startX: 14, startY: 16, cellSize: 25 },
};

const BOARD_IMAGES: Record<string, string> = {
  'Shadow of Babel': boardSob,
  'Broken Covenant': boardBc,
  'Arctic Archives': boardAa,
};

const COLS = 'ABCDEFGHIJKLMNOPQRSTUVW'.split('');
const ROWS = Array.from({ length: 32 }, (_, i) => i + 1);

function cellToIndex(cell: string): { col: number; row: number } | null {
  if (!cell || cell.length < 2) return null;
  const col = COLS.indexOf(cell[0]);
  const row = parseInt(cell.slice(1), 10) - 1;
  if (col === -1 || isNaN(row)) return null;
  return { col, row };
}

function tokenLabel(character: string): string {
  return character.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function tokenFontSize(character: string, cellSize: number): number {
  const raw = character.replace(/_/g, '');
  return Math.min(cellSize * 0.38, cellSize * 1.1 / raw.length);
}

function cellCoords(cell: string, cfg: { startX: number; startY: number; cellSize: number }) {
  const idx = cellToIndex(cell);
  if (!idx) return null;
  return {
    x: cfg.startX + idx.col * cfg.cellSize,
    y: cfg.startY + idx.row * cfg.cellSize,
  };
}

interface Props {
  view: GameView;
  playerName: string;
  pendingPath: string[];
  onCellClick: (cell: string) => void;
}

export default function Board({ view, playerName, pendingPath, onCellClick }: Props) {
  const [imgSize, setImgSize] = useState<{ w: number; h: number } | null>(null);

  const cfg = BOARD_CONFIGS[view.board_name] ?? BOARD_CONFIGS['Shadow of Babel'];
  const imgSrc = BOARD_IMAGES[view.board_name] ?? boardSob;

  const isAgent = view.role === 'agent';
  const isMyHunterTurn =
    view.role === 'hunter' &&
    view.phase === 'HUNTER_TURN' &&
    view.hunter_order[view.active_hunter_index] === playerName;
  const isAgentTurn = isAgent && view.phase === 'AGENT_TURN';
  const clickable = isAgentTurn || isMyHunterTurn;

  const pendingSet = new Set(pendingPath);
  const pathCells = pendingPath.length > 0
    ? pendingPath.map((cell, i) => ({ cell, idx: i }))
    : [];

  return (
    <div className={styles.boardWrap}>
      <div className={styles.container}>
        <img
          src={imgSrc}
          alt={view.board_name}
          className={styles.boardImg}
          onLoad={e => {
            const el = e.currentTarget;
            setImgSize({ w: el.naturalWidth, h: el.naturalHeight });
          }}
        />

        {imgSize && (
          <svg
            className={styles.overlay}
            viewBox={`0 0 ${imgSize.w} ${imgSize.h}`}
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Clickable grid cells */}
            {ROWS.map(row =>
              COLS.map(col => {
                const cell = `${col}${row}`;
                const x = cfg.startX + COLS.indexOf(col) * cfg.cellSize;
                const y = cfg.startY + (row - 1) * cfg.cellSize;
                const inPath = pendingSet.has(cell);

                return (
                  <rect
                    key={cell}
                    x={x}
                    y={y}
                    width={cfg.cellSize}
                    height={cfg.cellSize}
                    fill={inPath ? 'rgba(200,160,60,0.35)' : 'transparent'}
                    stroke={clickable ? 'rgba(255,255,255,0.08)' : 'none'}
                    strokeWidth={0.5}
                    style={{ cursor: clickable ? 'pointer' : 'default' }}
                    onClick={() => clickable && onCellClick(cell)}
                  />
                );
              })
            )}

            {/* Path line */}
            {pathCells.length > 1 && (
              <polyline
                points={pathCells
                  .map(({ cell }) => {
                    const coords = cellCoords(cell, cfg);
                    if (!coords) return '';
                    const cx = coords.x + cfg.cellSize / 2;
                    const cy = coords.y + cfg.cellSize / 2;
                    return `${cx},${cy}`;
                  })
                  .join(' ')}
                fill="none"
                stroke="rgba(200,160,60,0.8)"
                strokeWidth={1.5}
                strokeDasharray="3 2"
              />
            )}

            {/* Hunter positions */}
            {view.hunters.map(h => {
              const coords = cellCoords(h.position, cfg);
              if (!coords) return null;
              const cx = coords.x + cfg.cellSize / 2;
              const cy = coords.y + cfg.cellSize / 2;
              const isMe = h.player_name === playerName;
              return (
                <g key={h.player_name}>
                  <circle
                    cx={cx} cy={cy}
                    r={cfg.cellSize * 0.35}
                    fill={isMe ? '#4080c0' : '#206080'}
                    stroke="#a0d0ff"
                    strokeWidth={0.8}
                  />
                  <text
                    x={cx} y={cy + 0.5}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={tokenFontSize(h.character, cfg.cellSize)}
                    fill="white"
                    style={{ pointerEvents: 'none' }}
                  >
                    {tokenLabel(h.character)}
                  </text>
                </g>
              );
            })}

            {/* Vehicle */}
            {(() => {
              const coords = cellCoords(view.vehicle.position, cfg);
              if (!coords) return null;
              const cx = coords.x + cfg.cellSize / 2;
              const cy = coords.y + cfg.cellSize / 2;
              return (
                <g>
                  <rect
                    x={coords.x + 1} y={coords.y + 1}
                    width={cfg.cellSize - 2} height={cfg.cellSize - 2}
                    fill="rgba(80,160,80,0.5)"
                    stroke="#80c080"
                    strokeWidth={0.8}
                  />
                  <text
                    x={cx} y={cy + 1}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={cfg.cellSize * 0.4}
                    fill="white"
                    style={{ pointerEvents: 'none' }}
                  >
                    V
                  </text>
                </g>
              );
            })()}

            {/* Agent position (agent self-view) */}
            {view.role === 'agent' && (() => {
              const coords = cellCoords(view.agent.position, cfg);
              if (!coords) return null;
              const cx = coords.x + cfg.cellSize / 2;
              const cy = coords.y + cfg.cellSize / 2;
              const label = tokenLabel(view.agent.character);
              return (
                <g>
                  <circle cx={cx} cy={cy} r={cfg.cellSize * 0.35} fill="#c02020" stroke="#ff7070" strokeWidth={0.8} />
                  <text
                    x={cx} y={cy + 0.5}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={tokenFontSize(view.agent.character, cfg.cellSize)}
                    fill="white"
                    style={{ pointerEvents: 'none' }}
                  >
                    {label}
                  </text>
                </g>
              );
            })()}

            {/* Agent position visible to hunters */}
            {view.role === 'hunter' && view.agent.position && (() => {
              const coords = cellCoords(view.agent.position, cfg);
              if (!coords) return null;
              const cx = coords.x + cfg.cellSize / 2;
              const cy = coords.y + cfg.cellSize / 2;
              const character = view.agent.character;
              return (
                <g>
                  <circle cx={cx} cy={cy} r={cfg.cellSize * 0.35} fill="#c02020" stroke="#ff7070" strokeWidth={0.8} />
                  <text
                    x={cx} y={cy + 0.5}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={character ? tokenFontSize(character, cfg.cellSize) : cfg.cellSize * 0.4}
                    fill="white"
                    style={{ pointerEvents: 'none' }}
                  >
                    {character ? tokenLabel(character) : 'A'}
                  </text>
                </g>
              );
            })()}

            {/* Last-seen token — hidden when agent is currently visible */}
            {view.agent.last_seen_cell && !view.agent.position && (() => {
              const coords = cellCoords(view.agent.last_seen_cell, cfg);
              if (!coords) return null;
              const cx = coords.x + cfg.cellSize / 2;
              const cy = coords.y + cfg.cellSize / 2;
              const character = view.agent.character;
              return (
                <g>
                  <circle cx={cx} cy={cy} r={cfg.cellSize * 0.3} fill="rgba(192,32,32,0.15)" stroke="#c08040" strokeWidth={1} strokeDasharray="2 1" />
                  <text
                    x={cx} y={cy + 0.5}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={character ? tokenFontSize(character, cfg.cellSize) : cfg.cellSize * 0.35}
                    fill="#c08040"
                    style={{ pointerEvents: 'none' }}
                  >
                    {character ? tokenLabel(character) : '?'}
                  </text>
                </g>
              );
            })()}

            {/* Objectives:
                  Agent — always sees all 4 locations with completion state.
                  Hunters (2–3p, objectives_visible) — see all locations with completion state.
                  Hunters (4–5p, objectives hidden) — only see publicly completed locations. */}
            {(view.role === 'agent' || view.objectives_visible)
              ? view.objectives?.map(obj => {
                  const coords = cellCoords(obj, cfg);
                  if (!coords) return null;
                  const cx = coords.x + cfg.cellSize / 2;
                  const cy = coords.y + cfg.cellSize / 2;
                  const completed = view.role === 'agent'
                    ? view.agent.public_objectives.includes(obj) || view.agent.pending_objectives.includes(obj)
                    : view.agent.public_objectives.includes(obj);
                  return (
                    <circle
                      key={`obj-${obj}`}
                      cx={cx} cy={cy}
                      r={cfg.cellSize * 0.28}
                      fill={completed ? 'rgba(60,200,60,0.4)' : 'none'}
                      stroke={completed ? '#40c040' : 'rgba(60,160,200,0.6)'}
                      strokeWidth={0.8}
                    />
                  );
                })
              : view.agent.public_objectives.map(obj => {
                  const coords = cellCoords(obj, cfg);
                  if (!coords) return null;
                  const cx = coords.x + cfg.cellSize / 2;
                  const cy = coords.y + cfg.cellSize / 2;
                  return (
                    <circle
                      key={`obj-${obj}`}
                      cx={cx} cy={cy}
                      r={cfg.cellSize * 0.28}
                      fill="rgba(60,200,60,0.4)"
                      stroke="#40c040"
                      strokeWidth={0.8}
                    />
                  );
                })
            }
          </svg>
        )}
      </div>
    </div>
  );
}
