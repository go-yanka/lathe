OUT_DIR = r"projects/agentic-harness/goals/tetris-9b-experiment"
MODULE_NAME = "tetris_page"
HEADER = ""
GLUE = ""
FUNCTIONS = []
ARTIFACTS = [
    {
        "path": "_artifacts/tetris.html",
        "model": "openai:local",
        "prompt": "Create a COMPLETE single-file HTML page implementing a fully playable Tetris game. "
                  "The file must start with <!DOCTYPE html> and contain ALL CSS inside a <style> tag and ALL JavaScript inside a <script> tag - "
                  "no external URLs, no CDN links, no imports; it must work when opened directly from disk. "
                  "Requirements: "
                  "(1) A <canvas> element rendering a 10 column by 20 row Tetris grid with visible cell borders. "
                  "(2) All 7 tetromino shapes (I, O, T, S, Z, J, L) each with a distinct color. "
                  "(3) Keyboard controls: ArrowLeft and ArrowRight move the falling piece horizontally with collision checks against walls and stacked blocks; "
                  "ArrowUp rotates the piece clockwise with wall-kick attempts (try offsets like 0, -1, +1, -2, +2 and keep the first non-colliding position, otherwise cancel the rotation); "
                  "ArrowDown performs a soft drop (move down one row immediately); "
                  "Space performs a hard drop (piece falls instantly to its final resting position and locks). "
                  "Prevent default browser scrolling for these keys. "
                  "(4) When one or more rows are completely filled, briefly flash those rows (e.g. white highlight for a few animation frames or ~200ms) before removing them, "
                  "then shift the rows above down and award points (more points for multiple simultaneous lines, scaled by level). "
                  "(5) A visible score panel showing Score, Lines, and Level; level increases every 10 cleared lines and the gravity drop interval speeds up with each level. "
                  "(6) A next-piece preview box (a small second canvas or drawn region) showing the upcoming tetromino. "
                  "(7) Game over detection when a new piece cannot spawn: show an overlay with 'Game Over', the final score, and the text 'Press R to restart'; "
                  "pressing the R key resets the board, score, lines, level, and speed and starts a new game. "
                  "Use requestAnimationFrame or setInterval-style timing driven by the current level's drop interval. "
                  "Keep all game state (grid array, current piece, next piece, score, lines, level, gameOver flag) in JavaScript variables. "
                  "Style the page with a dark background, centered layout, and clear readable HUD text. "
                  "Output ONLY the file contents - no prose, no markdown.",
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
