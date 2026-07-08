OUT_DIR = r"projects/agentic-harness/goals/tetris-9b-experiment"
MODULE_NAME = "tetris_page"
HEADER = ""
GLUE = ""
FUNCTIONS = []
ARTIFACTS = [
    {
        "path": "_artifacts/tetris.html",
        "model": "openai:local",
        "prompt": (
            "Fill in the __FILL__ marker with ONLY a single JavaScript const declaration for all 7 Tetris pieces. "
            "Output ONLY the line starting with 'const PIECES = [' and ending with '];' - nothing else, no explanation. "
            "Each entry has two fields: shape (a 4x4 array of 0s and 1s) and color (a CSS hex string). "
            "WORKED EXAMPLE - the I piece entry looks like this: "
            "{ shape: [[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]], color: '#00f0f0' } "
            "Required order: I (cyan #00f0f0), O (yellow #f0f000), T (purple #a000f0), "
            "S (green #00f000), Z (red #f00000), J (blue #0000f0), L (orange #f0a000). "
            "Output ONLY: const PIECES = [ ...exactly 7 objects... ];"
        ),
        "skeleton": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Tetris</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #1a1a2e; display: flex; justify-content: center; align-items: center; min-height: 100vh; font-family: monospace; color: #fff; }
#container { display: flex; gap: 20px; align-items: flex-start; }
canvas#board { border: 2px solid #444; background: #0a0a0a; }
#sidebar { display: flex; flex-direction: column; gap: 15px; min-width: 130px; }
.panel { background: #16213e; border: 1px solid #444; padding: 10px; border-radius: 4px; }
.panel h3 { font-size: 12px; color: #aaa; margin-bottom: 6px; text-transform: uppercase; }
.panel .val { font-size: 22px; color: #eee; }
canvas#preview { border: 1px solid #444; background: #0a0a0a; display: block; margin: 0 auto; }
#gameover { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.78); justify-content: center; align-items: center; flex-direction: column; gap: 14px; }
#gameover.show { display: flex; }
#gameover h2 { font-size: 38px; color: #ff4444; }
#gameover p { font-size: 18px; }
</style>
</head>
<body>
<div id="container">
  <canvas id="board" width="300" height="600"></canvas>
  <div id="sidebar">
    <div class="panel"><h3>Score</h3><div class="val" id="scoreVal">0</div></div>
    <div class="panel"><h3>Lines</h3><div class="val" id="linesVal">0</div></div>
    <div class="panel"><h3>Level</h3><div class="val" id="levelVal">1</div></div>
    <div class="panel"><h3>Next</h3><canvas id="preview" width="120" height="120"></canvas></div>
  </div>
</div>
<div id="gameover">
  <h2>Game Over</h2>
  <p id="finalScore"></p>
  <p>Press R to restart</p>
</div>
<script>
__FILL__

const COLS = 10, ROWS = 20, CELL = 30;
const board = document.getElementById('board');
const bctx = board.getContext('2d');
const preview = document.getElementById('preview');
const pctx = preview.getContext('2d');
const scoreEl = document.getElementById('scoreVal');
const linesEl = document.getElementById('linesVal');
const levelEl = document.getElementById('levelVal');
const gameoverEl = document.getElementById('gameover');
const finalScoreEl = document.getElementById('finalScore');

let grid, cur, nxt, score, lines, level, gameOver, lastTime, elapsed, dropInterval, flashRows, flashTimer;

function emptyGrid() {
  return Array.from({length: ROWS}, () => new Array(COLS).fill(0));
}

function randPiece() {
  const p = PIECES[Math.floor(Math.random() * PIECES.length)];
  return { shape: p.shape.map(function(r) { return r.slice(); }), color: p.color, x: 3, y: 0 };
}

function rotate(shape) {
  const N = shape.length;
  const out = Array.from({length: N}, () => new Array(N).fill(0));
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) out[x][N - 1 - y] = shape[y][x];
  return out;
}

function collides(shape, ox, oy) {
  for (let y = 0; y < shape.length; y++)
    for (let x = 0; x < shape[y].length; x++)
      if (shape[y][x]) {
        const cx = ox + x, cy = oy + y;
        if (cx < 0 || cx >= COLS || cy >= ROWS) return true;
        if (cy >= 0 && grid[cy][cx]) return true;
      }
  return false;
}

function lock() {
  for (let y = 0; y < cur.shape.length; y++)
    for (let x = 0; x < cur.shape[y].length; x++)
      if (cur.shape[y][x] && cur.y + y >= 0)
        grid[cur.y + y][cur.x + x] = cur.color;
  const full = [];
  for (let r = ROWS - 1; r >= 0; r--)
    if (grid[r].every(function(c) { return c; })) full.push(r);
  if (full.length) {
    flashRows = full;
    flashTimer = 200;
  } else {
    spawn();
  }
}

function clearLines() {
  const pts = [0, 100, 300, 500, 800];
  lines += flashRows.length;
  score += (pts[flashRows.length] || 800) * level;
  flashRows.slice().sort(function(a, b) { return b - a; }).forEach(function(r) {
    grid.splice(r, 1);
    grid.unshift(new Array(COLS).fill(0));
  });
  level = Math.floor(lines / 10) + 1;
  dropInterval = Math.max(100, 1000 - (level - 1) * 90);
  flashRows = [];
  scoreEl.textContent = score;
  linesEl.textContent = lines;
  levelEl.textContent = level;
  spawn();
}

function spawn() {
  cur = nxt || randPiece();
  nxt = randPiece();
  elapsed = 0;
  if (collides(cur.shape, cur.x, cur.y)) {
    gameOver = true;
    finalScoreEl.textContent = 'Score: ' + score;
    gameoverEl.classList.add('show');
    return;
  }
  drawPreview();
}

function drawCell(ctx, x, y, color, size) {
  ctx.fillStyle = color;
  ctx.fillRect(x * size + 1, y * size + 1, size - 2, size - 2);
  ctx.strokeStyle = 'rgba(255,255,255,0.18)';
  ctx.strokeRect(x * size + 0.5, y * size + 0.5, size - 1, size - 1);
}

function drawBoard() {
  bctx.clearRect(0, 0, board.width, board.height);
  bctx.strokeStyle = '#1e1e1e';
  for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++)
    bctx.strokeRect(c * CELL, r * CELL, CELL, CELL);
  for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++)
    if (grid[r][c]) {
      if (flashRows.indexOf(r) !== -1 && flashTimer > 0)
        drawCell(bctx, c, r, '#ffffff', CELL);
      else
        drawCell(bctx, c, r, grid[r][c], CELL);
    }
  var gy = cur.y;
  while (!collides(cur.shape, cur.x, gy + 1)) gy++;
  if (gy !== cur.y)
    for (let y = 0; y < cur.shape.length; y++) for (let x = 0; x < cur.shape[y].length; x++)
      if (cur.shape[y][x]) {
        bctx.fillStyle = 'rgba(255,255,255,0.13)';
        bctx.fillRect((cur.x + x) * CELL + 1, (gy + y) * CELL + 1, CELL - 2, CELL - 2);
      }
  for (let y = 0; y < cur.shape.length; y++) for (let x = 0; x < cur.shape[y].length; x++)
    if (cur.shape[y][x]) drawCell(bctx, cur.x + x, cur.y + y, cur.color, CELL);
}

function drawPreview() {
  pctx.clearRect(0, 0, preview.width, preview.height);
  var sz = 24;
  var ox = Math.floor((preview.width - 4 * sz) / 2);
  var oy = Math.floor((preview.height - 4 * sz) / 2);
  for (let y = 0; y < nxt.shape.length; y++) for (let x = 0; x < nxt.shape[y].length; x++)
    if (nxt.shape[y][x]) {
      pctx.fillStyle = nxt.color;
      pctx.fillRect(ox + x * sz + 1, oy + y * sz + 1, sz - 2, sz - 2);
    }
}

function init() {
  grid = emptyGrid();
  score = 0; lines = 0; level = 1; gameOver = false;
  dropInterval = 1000; elapsed = 0; lastTime = null;
  flashRows = []; flashTimer = 0;
  scoreEl.textContent = '0'; linesEl.textContent = '0'; levelEl.textContent = '1';
  gameoverEl.classList.remove('show');
  nxt = randPiece();
  spawn();
  requestAnimationFrame(loop);
}

function loop(ts) {
  if (gameOver) return;
  if (!lastTime) lastTime = ts;
  var dt = ts - lastTime;
  lastTime = ts;
  if (flashTimer > 0) {
    flashTimer -= dt;
    if (flashTimer <= 0) clearLines();
  } else {
    elapsed += dt;
    if (elapsed >= dropInterval) {
      elapsed -= dropInterval;
      if (!collides(cur.shape, cur.x, cur.y + 1)) cur.y++;
      else lock();
    }
  }
  drawBoard();
  requestAnimationFrame(loop);
}

document.addEventListener('keydown', function(e) {
  if (['ArrowLeft','ArrowRight','ArrowUp','ArrowDown',' '].indexOf(e.key) !== -1) e.preventDefault();
  if (gameOver) { if (e.key === 'r' || e.key === 'R') init(); return; }
  if (flashTimer > 0) return;
  if (e.key === 'ArrowLeft' && !collides(cur.shape, cur.x - 1, cur.y)) cur.x--;
  if (e.key === 'ArrowRight' && !collides(cur.shape, cur.x + 1, cur.y)) cur.x++;
  if (e.key === 'ArrowDown') {
    if (!collides(cur.shape, cur.x, cur.y + 1)) cur.y++;
    else lock();
  }
  if (e.key === 'ArrowUp') {
    var rot = rotate(cur.shape);
    var kicks = [0, -1, 1, -2, 2];
    for (var i = 0; i < kicks.length; i++) {
      if (!collides(rot, cur.x + kicks[i], cur.y)) { cur.shape = rot; cur.x += kicks[i]; break; }
    }
  }
  if (e.key === ' ') {
    while (!collides(cur.shape, cur.x, cur.y + 1)) cur.y++;
    lock();
  }
  if (e.key === 'r' || e.key === 'R') init();
  drawBoard();
});

init();
</script>
</body>
</html>""",
        "tests": [
            "assert '<!doctype html' in content.lower()",
            "assert '<canvas' in content.lower()",
            "assert '<script' in content.lower()",
            "assert '<style' in content.lower()",
            "assert 'arrowleft' in content.lower()",
            "assert 'arrowright' in content.lower()",
            "assert 'arrowup' in content.lower()",
            "assert 'arrowdown' in content.lower()",
            "assert 'score' in content.lower()",
            "assert 'level' in content.lower()",
            "assert 'lines' in content.lower()",
            "assert 'game over' in content.lower()",
            "assert 'next' in content.lower()",
            "assert 'http://' not in content.lower() and 'https://' not in content.lower()"
        ],
        "functional_ref": "web_canvas_game"
    }
]