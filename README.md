# icefold-sdk

The slim, shared kernel for **IceFold**: the worker-control WebSocket protocol
plus a small on-runner helper kit. It ships no node implementations — the
server renders each node into a self-contained `.py` bundle and the
[`icefold-runner`](https://pypi.org/project/icefold-runner/) imports the bundle
on demand.

> **Import name:** the distribution is `icefold-sdk`, but it installs as the
> top-level package `icefold` (like `pyyaml` → `import yaml`).

```python
import icefold
print(icefold.__version__)
```

Both the IceFold server and the runner depend on this package: the server uses
the wire / id / log surface to talk to its workers; the runner uses the same
wire protocol to dial back, then imports server-rendered bundles to run jobs.

## Surface

| Module | What |
|---|---|
| `icefold.wire` | `/v1/ws/worker` frames: `make_node_exec`, `make_missing_dep`, `binary_install_hint`; constants (`SRV_NODE_EXEC`, `WKR_NODE_DONE`, …); `OUTPUT_UPLOAD_PATH` |
| `icefold.crypto` | XOR-keystream framing for the worker WS (`xor_bytes`) |
| `icefold._logging` | Coloured stdout logger (`log_info`, `log_warning`, `log_error`, `log_debug`) |
| `icefold.ids` | `get_file_id()` — time-ordered unique id for output filenames |
| `icefold.config` | `DATA_DIR` / `DOWNLOAD_BASE_DIR` / `UPLOAD_BASE_DIR` (driven by `ICEFOLD_PROJECT_ROOT`) |
| `icefold.exceptions` | `AppError` family + `MissingDependencyError` |
| `icefold.runtime` | `run_blocking(fn, *a, **kw)` + `write_text(path, content)` — off-event-loop IO helpers |
| `icefold.__init__` | Slim re-export: `log_* / get_file_id / run_blocking / write_text` |

## Install

```bash
pip install icefold-sdk           # runner-side helpers + wire protocol
```

Requires Python ≥ 3.11. This package is the shared protocol layer; if you want
to run IceFold nodes on your own machine, install
[`icefold-runner`](https://pypi.org/project/icefold-runner/) instead (it pulls
this in).
