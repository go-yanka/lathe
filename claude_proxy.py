#!/usr/bin/env python3
"""
Minimal OpenAI-compatible proxy that wraps the Claude Code CLI (subscription, no API key).

a prior agent Desktop has no native "claude_cli" provider — its Anthropic option needs a
metered API key. This proxy exposes /v1/chat/completions and /v1/models, and for each
request shells out to `claude -p ...` which authenticates via the user's Claude
subscription (claude login), so there is ZERO per-token cost.

Reuses the proven stream-json translation + Windows subprocess handling from the
old WSL router (backed up at C:\\a prior agent-backup-20260605\\router.py).

Run:  python claude_proxy.py --port 8787
Point a prior agent Desktop custom provider base_url at: http://127.0.0.1:8787/v1
"""
import argparse
import asyncio
import base64
import json
import os
import subprocess
import time
import uuid
import logging
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("claude-proxy")

# Resolve the Windows claude launcher (the npm .cmd shim).
CLAUDE_BIN = os.environ.get(
    "CLAUDE_BIN",
    os.path.expandvars(r"%APPDATA%\npm\claude.cmd"),
)
DEFAULT_MODEL = os.environ.get("CLAUDE_PROXY_MODEL", "sonnet")  # haiku|sonnet|opus
TIMEOUT = float(os.environ.get("CLAUDE_PROXY_TIMEOUT", "600"))

app = FastAPI()


def _flatten(content):
    if isinstance(content, list):
        return " ".join(
            p.get("text", "")
            for p in content
            if isinstance(p, dict) and p.get("type") == "text"
        )
    return content or ""


# Vision support: `claude -p` is text-in, but Claude Code CAN read image FILES via its Read tool.
# So when a request carries image_url blocks, we save each image to a local file (inside the proxy's
# cwd so Claude Code is allowed to read it) and hand the path to Claude with the Read tool enabled.
IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_img_tmp")


def _extract_images(messages):
    """Pull image_url blocks out of OpenAI-format messages → save each inline image to a local file.
    Returns (local_paths, remote_urls). Only inline data: URLs can be read by Claude Code; http(s)
    URLs are noted but not fetched (Claude Code reads files, not the web)."""
    local, remote = [], []
    for m in messages:
        content = m.get("content")
        if not isinstance(content, list):
            continue
        for p in content:
            if not (isinstance(p, dict) and p.get("type") == "image_url"):
                continue
            url = ((p.get("image_url") or {}).get("url") or "").strip()
            if url.startswith("data:"):
                try:
                    header, b64 = url.split(",", 1)
                    ext = "png" if "png" in header.lower() else ("webp" if "webp" in header.lower() else "jpg")
                    os.makedirs(IMG_DIR, exist_ok=True)
                    fn = os.path.join(IMG_DIR, f"img_{uuid.uuid4().hex[:12]}.{ext}")
                    with open(fn, "wb") as f:
                        f.write(base64.b64decode(b64))
                    local.append(fn)
                except Exception:
                    log.exception("failed to save inline image")
            elif url.startswith("http"):
                remote.append(url)
    return local, remote


def _build_prompt(messages):
    """Concatenate the conversation into a single prompt for `claude -p`."""
    parts = []
    for m in messages:
        role = m.get("role", "user")
        text = _flatten(m.get("content"))
        if not text:
            continue
        if role == "system":
            parts.append(text)
        else:
            parts.append(f"[{role}] {text}")
    return "\n\n".join(parts)


def _map_model(requested: str) -> str:
    """Map whatever a prior agent sends to a claude --model alias."""
    if not requested:
        return DEFAULT_MODEL
    r = requested.lower()
    for alias in ("haiku", "sonnet", "opus"):
        if alias in r:
            return alias
    return DEFAULT_MODEL


def _base_cmd(model: str, with_read: bool = False):
    # Pure text completion: NO tools, no autonomous edits. The harness's level-2 calls (analysis,
    # cover letters, code/HTML artifact generation) only need text out. The agentic toolset +
    # acceptEdits made large generations (e.g. a full settings.html) run the CLI past the 600s
    # timeout; disabling tools makes them plain, fast completions.
    # with_read=True (image requests only): whitelist JUST the Read tool so Claude Code can view the
    # saved image file(s) — still no edits, no shell, no web.
    return [
        CLAUDE_BIN, "-p",
        "--model", model,
        "--allowedTools", ("Read" if with_read else ""),
    ]


@app.get("/v1/models")
async def list_models():
    created = int(time.time())
    return {
        "object": "list",
        "data": [
            {"id": m, "object": "model", "created": created, "owned_by": "anthropic-cli"}
            for m in ("claude-cli", "haiku", "sonnet", "opus")
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "bin": CLAUDE_BIN, "default_model": DEFAULT_MODEL}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    stream = bool(body.get("stream"))
    model = _map_model(body.get("model", ""))
    prompt = _build_prompt(messages)
    # Vision: if the request carries images, save them to files and tell Claude to Read them.
    local_imgs, remote_imgs = _extract_images(messages)
    with_read = bool(local_imgs)
    if local_imgs:
        prompt += ("\n\n[The user attached image file(s). Use the Read tool to open each path below, "
                   "then answer based on what the image(s) show:\n" + "\n".join(local_imgs) + "]")
    if remote_imgs:
        prompt += ("\n\n[The user referenced image URL(s) that cannot be opened here: "
                   + ", ".join(remote_imgs) + "]")
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    if not stream:
        # Synchronous run (Windows .cmd needs subprocess.run, not asyncio exec).
        def _run():
            return subprocess.run(
                _base_cmd(model, with_read),
                input=prompt,
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=TIMEOUT, shell=False,
            )
        try:
            r = await asyncio.get_event_loop().run_in_executor(None, _run)
            content = (r.stdout or "").strip()
            if r.returncode != 0 and not content:
                content = f"[claude_cli error rc={r.returncode}: {(r.stderr or '')[:400]}]"
        except Exception as e:
            log.exception("claude run failed")
            content = f"[claude_cli error: {e}]"
        return JSONResponse({
            "id": chat_id, "object": "chat.completion", "created": created,
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })

    # Streaming via native stream-json (proven approach from old router).
    stream_cmd = _base_cmd(model, with_read) + [
        "--output-format", "stream-json", "--verbose", "--include-partial-messages",
    ]

    def _chunk(*, content=None, role=None, finish=None):
        delta = {}
        if role is not None:
            delta["role"] = role
        if content is not None:
            delta["content"] = content
        return (f"data: " + json.dumps({
            "id": chat_id, "object": "chat.completion.chunk", "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }) + "\n\n").encode()

    async def gen() -> AsyncIterator[bytes]:
        try:
            proc = await asyncio.create_subprocess_exec(
                *stream_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            log.exception("stream spawn failed")
            yield _chunk(role="assistant", content=f"[spawn error: {e}]", finish="stop")
            yield b"data: [DONE]\n\n"
            return
        yield _chunk(role="assistant")
        try:
            proc.stdin.write(prompt.encode("utf-8", "replace"))
            await proc.stdin.drain()
            proc.stdin.close()
        except Exception:
            log.exception("stdin write failed")
        sent_finish = False
        got_text = False  # did we emit ANY assistant text? guards against empty-response retries
        try:
            while True:
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=300.0)
                except asyncio.TimeoutError:
                    yield _chunk(content="")
                    continue
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    continue
                etype = evt.get("type")
                if etype == "stream_event":
                    inner = evt.get("event") or {}
                    itype = inner.get("type")
                    if itype == "content_block_delta":
                        d = inner.get("delta") or {}
                        if d.get("type") == "text_delta":
                            t = d.get("text") or ""
                            if t:
                                got_text = True
                                yield _chunk(content=t)
                        elif d.get("type") == "thinking_delta":
                            yield _chunk(content="")
                    elif itype == "content_block_start":
                        yield _chunk(content="")
                    elif itype == "message_stop":
                        yield _chunk(finish="stop")
                        yield b"data: [DONE]\n\n"
                        sent_finish = True
                elif etype == "result":
                    # Claude CLI is itself an agent: the final answer is here in `result`.
                    # If streaming produced no text (tool-only turn, image request,
                    # thinking-only, etc.) emit the result text so a prior agent never sees an
                    # empty response and retry-storms.
                    result_text = (evt.get("result") or "").strip()
                    if not sent_finish:
                        if evt.get("is_error"):
                            yield _chunk(content=f"\n[error: {result_text}]", finish="stop")
                        else:
                            if not got_text and result_text:
                                got_text = True
                                yield _chunk(content=result_text)
                            elif not got_text:
                                # truly nothing came back — say so rather than empty
                                yield _chunk(content="[claude_cli: no output returned]")
                            yield _chunk(finish="stop")
                        yield b"data: [DONE]\n\n"
                        sent_finish = True
                    break
        except asyncio.CancelledError:
            try: proc.kill()
            except Exception: pass
            raise
        finally:
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except Exception:
                try: proc.kill()
                except Exception: pass
            if not sent_finish:
                if not got_text:
                    yield _chunk(content="[claude_cli: stream ended with no output]")
                yield _chunk(finish="stop")
                yield b"data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    log.info("claude-proxy starting on http://%s:%d  bin=%s default_model=%s",
             args.host, args.port, CLAUDE_BIN, DEFAULT_MODEL)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
