"""T6 — request_spec: the loop's call to the analyst (Claude) via the :8787 CLI proxy.
Thin I/O. Plugs into autonomy_loop's deps['request_spec'].

RESILIENT: the Claude proxy is supervised but can blip/restart. A bare urlopen that RAISES
on any non-200 used to propagate straight out of the self-feed cycle and kill it with a silent
exit 1 (no ledger line, no alert). So we retry a few times with brief backoff and, if the proxy
is genuinely unreachable, return "" — the loop then degrades to a logged plan_rejected and tries
again next cycle instead of crashing."""
import json
import os
import sys
import time
import urllib.request

# #12 L2: optional usage reporter. lathe.py main() binds this to the run manifest so every analyst call's
# measured tokens are attributed. Never required, never raises into the caller.
USAGE_HOOK = None


def request_spec(prompt, url=None, timeout=None, retries=None, images=None, model=None):
    """POST `prompt` to the Claude CLI proxy, return the response text (the next plan).
    Returns "" (never raises) if the proxy stays unreachable across retries, so a transient
    proxy outage degrades gracefully instead of killing the autonomy cycle.

    `images`: optional list of data-URI strings (e.g. "data:image/png;base64,...."). When given, the
    message content is sent in OpenAI multimodal form (text + image_url blocks) — the proxy saves each
    inline image and lets Claude view it. This is what the D3 vision judge uses to SEE a rendered page.
    `model`: override the analyst model (e.g. a vision-capable one) for this call."""
    url = url or os.environ.get("HARNESS_CLAUDE_URL", "http://127.0.0.1:8787/v1/chat/completions")
    from urllib.parse import urlparse, urlunparse            # SSRF/exfil guard
    pu = urlparse(url)
    if pu.scheme not in ("http", "https"):                   # only http(s), never file:// / ftp://
        sys.stderr.write("request_spec: refusing non-http(s) analyst URL: %s\n" % url)
        return ""
    _gai_pin = None                                          # pinned getaddrinfo result (set below) so urllib can't re-resolve
    if os.environ.get("LATHE_TRUST_REMOTE_ANALYST") != "1":  # RESOLVE to IPs (a hostname prefix is bypassable)
        import socket, ipaddress
        _host = pu.hostname or ""
        try:
            _ai = socket.getaddrinfo(_host, pu.port or (443 if pu.scheme == "https" else 80))
        except Exception:
            _ai = []
        _ips = {a[4][0] for a in _ai}

        def _safe(ip):
            try:
                a = ipaddress.ip_address(ip.split("%")[0])
                if getattr(a, "ipv4_mapped", None):           # ::ffff:169.254.x.y -> judge the embedded IPv4, not the v6 wrapper
                    a = a.ipv4_mapped
                return (a.is_loopback or a.is_private) and not (a.is_link_local or a.is_unspecified)  # block 169.254 metadata + 0.0.0.0/::
            except Exception:
                return False
        if not _ips or not all(_safe(i) for i in _ips):
            sys.stderr.write("request_spec: refusing non-local analyst host %s %s — set LATHE_TRUST_REMOTE_ANALYST=1\n"
                             % (_host, sorted(_ips)))
            return ""
        # PIN the connection to the vetted address for BOTH http and https: urllib re-resolves the hostname at
        # connect time, so DNS rebinding could swap a safe check-time IP for an internal one. Forcing getaddrinfo
        # to return only the vetted result closes that window; https still validates the cert vs the URL hostname.
        _gai_pin = [a for a in _ai if _safe(a[4][0])]
    timeout = timeout or int(os.environ.get("CLAUDE_TIMEOUT", "180"))   # 180: covers a full plan generation (the planner prompt + inventory is large); still bounds a wedged proxy
    retries = retries if retries is not None else int(os.environ.get("CLAUDE_RETRIES", "2"))
    retries = max(1, retries)
    _model = model or os.environ.get("HARNESS_ANALYST_MODEL", "sonnet")
    if images:                                               # D3: multimodal content (text + image_url blocks)
        _content = [{"type": "text", "text": prompt}]
        for _u in images:
            _content.append({"type": "image_url", "image_url": {"url": _u}})
    else:
        _content = prompt
    body = json.dumps({"model": _model,
                       "messages": [{"role": "user", "content": _content}],
                       "stream": False}).encode()
    # HEARTBEAT (observability whole-class fix): an analyst call is a single BLOCKING request that can take
    # minutes (drafting a whole webapp spec, a repair rewrite) with ZERO output — which reads as "stuck after
    # assumptions for 5 minutes, no idea what it's doing". A daemon thread prints an alive-signal every N
    # seconds while the call blocks, so a slow phase is never silent. Short calls (<N s) print nothing.
    # LATHE_HEARTBEAT=0 disables; LATHE_HEARTBEAT_SECS sets the interval. `label` names the phase.
    import threading
    _hb_stop = threading.Event()
    _hb_t0 = time.time()
    _hb_label = os.environ.get("LATHE_PHASE", "analyst")

    def _heartbeat():
        _iv = float(os.environ.get("LATHE_HEARTBEAT_SECS", "15"))
        while not _hb_stop.wait(_iv):
            try:
                sys.stderr.write("    .. %s still working (%ds) ..\n" % (_hb_label, int(time.time() - _hb_t0)))
                sys.stderr.flush()
            except Exception:
                pass
    if os.environ.get("LATHE_HEARTBEAT", "1") not in ("0", "off", "false"):
        threading.Thread(target=_heartbeat, daemon=True).start()
    last_err = None
    try:
      for attempt in range(retries):
        _orig_gai = None
        try:
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            if _gai_pin:                                     # force the socket to the vetted address (no rebind), then restore
                import socket as _sock
                _orig_gai = _sock.getaddrinfo
                _sock.getaddrinfo = lambda *a, **k: _gai_pin
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read(16 * 1024 * 1024))    # cap: a hostile endpoint can't OOM us
            if USAGE_HOOK:                               # #12 L2: report the analyst's measured usage upward
                try:
                    USAGE_HOOK("analyst", d.get("usage") or {})
                except Exception:
                    pass
            c = d["choices"][0]["message"]["content"]
            if isinstance(c, list):                      # Anthropic-style structured content -> flatten to text
                c = "".join(b.get("text", "") for b in c if isinstance(b, dict))
            return c if isinstance(c, str) else str(c)
        except Exception as e:                       # noqa: BLE001 — any failure is retryable here
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))        # brief backoff to ride out a proxy restart
        finally:
            if _orig_gai is not None:                # always restore the global resolver
                _sock.getaddrinfo = _orig_gai
      sys.stderr.write("request_spec: Claude proxy unreachable after %d tries: %s\n" % (retries, last_err))
      return ""
    finally:
        _hb_stop.set()                               # stop the heartbeat however we exit (return or error)
