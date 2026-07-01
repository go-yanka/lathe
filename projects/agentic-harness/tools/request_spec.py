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


def request_spec(prompt, url=None, timeout=None, retries=None):
    """POST `prompt` to the Claude CLI proxy, return the response text (the next plan).
    Returns "" (never raises) if the proxy stays unreachable across retries, so a transient
    proxy outage degrades gracefully instead of killing the autonomy cycle."""
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
    body = json.dumps({"model": os.environ.get("HARNESS_ANALYST_MODEL", "sonnet"),
                       "messages": [{"role": "user", "content": prompt}],
                       "stream": False}).encode()
    last_err = None
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
