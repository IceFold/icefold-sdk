"""Wire protocol for the ``/v1/ws/worker`` reverse channel.

One WebSocket connection per ``icefold-worker`` process carries a single
message family: **node exec**. The server ships one leaf ``execute_single``
invocation (already sliced to a single variant by the server-side variant
planner) and the worker streams back status then exactly one terminal frame.
Keyed by ``call_id``.

Frames are JSON objects. When an auth token is configured they travel as
binary WS frames XOR'd with the token (see ``app.worker.crypto``); otherwise
as plain-text JSON frames (dev fallback).

  Server → Worker
    node_exec : run one leaf call. Carries node_type + node_config + inputs
                (with media paths rewritten to URL paths the worker GETs),
                resolved provider/model, the variant coordinate, and a
                per-call timeout.
    cancel    : kill the in-flight call_id (best-effort).
    ping      : liveness probe; worker replies ``pong``.

  Worker → Server
    hello       : sent once right after connect. Announces worker_id/version.
    node_status : 0+ progress frames (phase + human message). Advisory only.
    node_done   : exactly one terminal frame per call_id. Carries the node
                  output (media paths already rewritten to server-canonical
                  paths via the HTTP upload round-trip), plus err/killed.
    ping        : upstream keepalive; server need not reply.
    pong        : reply to a server ping.
"""

from __future__ import annotations

# ── Server → Worker ──
SRV_NODE_EXEC = "node_exec"
SRV_CANCEL = "cancel"
SRV_PING = "ping"
# Reply to a ``WKR_NODE_CALLBACK`` request: the server resolved the requested
# capability (provider call for ``llm.*``; notification for ``progress``)
# and is returning the result. ``ok=False`` carries the error text so the
# bundle can surface it like any other call failure.
SRV_NODE_CALLBACK_RESULT = "node_callback_result"

# ── Worker → Server ──
WKR_HELLO = "hello"
WKR_NODE_STATUS = "node_status"
WKR_NODE_DONE = "node_done"
WKR_PING = "ping"
WKR_PONG = "pong"
# Sent in place of ``node_done`` when bundle pre-flight finds a runner host
# missing the bundle's declared ``python_deps`` / ``binary_deps``. The server
# surfaces a structured "install X via …" notification + lands the run in
# ERROR; the user installs and retries on their own runner.
WKR_MISSING_DEP = "missing_dep"
# Mid-run runner→server callback: the bundle asked for a server-only
# capability (LLM call, progress notification) and is awaiting a reply.
# Correlated by ``call_id`` (the parent node_exec) + ``req_id`` (this
# callback). ``kind`` picks the handler ("progress" / "llm.text" / …);
# ``payload`` is kind-specific.
WKR_NODE_CALLBACK = "node_callback"

# HTTP endpoint (path only; the worker prefixes its own http base) the worker
# POSTs output media files to. Kept here so both ends agree on one constant.
OUTPUT_UPLOAD_PATH = "/v1/workers/output"

# Default per-call deadline when a node_exec omits ``timeout_ms``. Generous
# because cpu_bound media work (long transcodes) legitimately runs for
# minutes; the server-side await adds a grace margin on top of this.
DEFAULT_EXEC_TIMEOUT_MS = 30 * 60 * 1000


def make_node_exec(
    *,
    call_id: str,
    node_id: str,
    node_type: str,
    node_config: dict,
    inputs: dict,
    user_id: str,
    session_id: str | None,
    space_name: str | None,
    provider: dict,
    model: str,
    variant: dict,
    timeout_ms: int,
    bundle_hash: str,
    bundle_url: str = "",
    python_deps: tuple = (),
    binary_deps: tuple = (),
) -> dict:
    """Build a ``node_exec`` frame.

    Bundle-only: the server has rendered a self-contained ``.py`` for this
    node and cached it; the runner fetches the bundle from ``bundle_url`` (or
    its local cache), pre-flights ``python_deps`` + ``binary_deps``, and calls
    ``__icefold_run__``.
    """
    if not bundle_hash:
        raise ValueError("make_node_exec requires bundle_hash (bundle-only wire)")
    return {
        "type": SRV_NODE_EXEC,
        "call_id": call_id,
        "node_id": node_id,
        "node_type": node_type,
        "node_config": node_config,
        "inputs": inputs,
        "user_id": user_id,
        "session_id": session_id or "",
        "space_name": space_name or "",
        "provider": provider,
        "model": model,
        "variant": variant,
        "timeout_ms": int(timeout_ms),
        "bundle_hash": bundle_hash,
        "bundle_url": bundle_url or "",
        "python_deps": list(python_deps),
        "binary_deps": list(binary_deps),
    }


# Per-platform install hint table for the dep-missing reply. Kept in the SDK
# so server + runner share one canonical wording; the runner fills these in
# based on its own ``sys.platform``.
_BINARY_INSTALL_HINTS: dict[str, dict[str, str]] = {
    "ffmpeg":  {"linux": "sudo apt install ffmpeg",
                "darwin": "brew install ffmpeg",
                "win32":  "winget install ffmpeg  (or: scoop install ffmpeg)"},
    "ffprobe": {"linux": "sudo apt install ffmpeg",
                "darwin": "brew install ffmpeg",
                "win32":  "winget install ffmpeg"},
}


def binary_install_hint(binary: str, platform: str) -> str:
    """Per-platform install command for ``binary`` (``linux``/``darwin``/``win32``)."""
    table = _BINARY_INSTALL_HINTS.get(binary)
    if not table:
        return f"install {binary} (no canned hint)"
    return table.get(platform) or table.get("linux") or f"install {binary}"


def make_node_callback(
    *,
    call_id: str,
    req_id: str,
    kind: str,
    payload: dict,
) -> dict:
    """Build a runner→server ``node_callback`` frame.

    The bundle is asking the host to perform a server-only capability:

      * ``kind="progress"``    — fire-and-forget; payload routes to the
                                  session SSE notifier on the server side.
      * ``kind="llm.text"``    — request/reply; payload carries
                                  ``{"prompt", "model"?, "image_url"?}``;
                                  server resolves provider + meters the
                                  call + returns the LLM response.

    ``req_id`` correlates the eventual ``node_callback_result``; the bundle
    awaits the matching reply.
    """
    return {
        "type": WKR_NODE_CALLBACK,
        "call_id": call_id,
        "req_id": req_id,
        "kind": kind,
        "payload": payload,
    }


def make_node_callback_result(
    *,
    call_id: str,
    req_id: str,
    ok: bool,
    result=None,
    error: str = "",
) -> dict:
    """Build a server→runner ``node_callback_result`` frame.

    Sent in reply to a ``node_callback`` with the matching ``(call_id,
    req_id)``. ``ok=False`` carries an error string the bundle can raise.
    Fire-and-forget callbacks (e.g. ``progress``) still get an ``ok=True``
    reply so the runner-side awaiter never hangs.
    """
    return {
        "type": SRV_NODE_CALLBACK_RESULT,
        "call_id": call_id,
        "req_id": req_id,
        "ok": bool(ok),
        "result": result,
        "error": error or "",
    }


def make_missing_dep(
    *,
    call_id: str,
    missing_binaries: tuple = (),
    missing_python: tuple = (),
    install_hint: str = "",
) -> dict:
    """Runner → server frame: bundle pre-flight failed; report what's missing."""
    return {
        "type": WKR_MISSING_DEP,
        "call_id": call_id,
        "missing_binaries": list(missing_binaries),
        "missing_python": list(missing_python),
        "install_hint": install_hint or "",
    }


if __name__ == "__main__":
    # Bundle path: server-side rendered, hash + URL + dep manifest only.
    frame = make_node_exec(
        call_id="c1", node_id="n1", node_type="UpperText", node_config={},
        inputs={"text": "hi"}, user_id="u", session_id=None, space_name=None,
        provider={}, model="", variant={}, timeout_ms=30_000,
        bundle_hash="abc", bundle_url="http://srv/v1/bundles/abc",
        python_deps=(), binary_deps=("ffmpeg",),
    )
    assert frame["type"] == SRV_NODE_EXEC and frame["bundle_hash"] == "abc"
    assert frame["binary_deps"] == ["ffmpeg"]
    assert "node_source" not in frame, "wire is bundle-only"

    # Bundle-only: an omitted bundle_hash is a programmer error.
    try:
        make_node_exec(
            call_id="c2", node_id="n2", node_type="OldNode", node_config={},
            inputs={}, user_id="u", session_id=None, space_name=None,
            provider={}, model="", variant={}, timeout_ms=30_000,
            bundle_hash="",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("empty bundle_hash must ValueError")

    # Missing-dep reply.
    msg = make_missing_dep(
        call_id="c1",
        missing_binaries=("ffmpeg",),
        missing_python=(),
        install_hint="install ffmpeg",
    )
    assert msg["type"] == WKR_MISSING_DEP and msg["missing_binaries"] == ["ffmpeg"]

    # Bundle-host callbacks (progress + llm.text).
    cb = make_node_callback(
        call_id="c1", req_id="r1",
        kind="progress", payload={"phase": "fetching", "node_id": "n1"},
    )
    assert cb["type"] == WKR_NODE_CALLBACK and cb["kind"] == "progress"
    assert cb["req_id"] == "r1" and cb["payload"]["phase"] == "fetching"

    cb_text = make_node_callback(
        call_id="c1", req_id="r2",
        kind="llm.text",
        payload={"prompt": "hi", "model": "openai/gpt-4o"},
    )
    assert cb_text["kind"] == "llm.text"

    res = make_node_callback_result(
        call_id="c1", req_id="r2", ok=True, result="hi back",
    )
    assert res["type"] == SRV_NODE_CALLBACK_RESULT and res["ok"] is True
    assert res["result"] == "hi back" and res["error"] == ""

    err = make_node_callback_result(
        call_id="c1", req_id="r3", ok=False, error="boom",
    )
    assert err["ok"] is False and err["error"] == "boom" and err["result"] is None

    # Platform-aware install hints.
    assert "brew install" in binary_install_hint("ffmpeg", "darwin")
    assert "apt" in binary_install_hint("ffmpeg", "linux")
    assert "no canned hint" in binary_install_hint("nonexistent", "linux")

    print("wire: OK")
