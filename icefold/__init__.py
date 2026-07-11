"""icefold — the slim, runner-side shared surface for IceFold.

This is the narrow shared kernel the IceFold server and the icefold-runner
both depend on: the worker-control wire protocol plus a tiny on-runner helper
kit. It ships no node implementations — the server renders each node into a
self-contained bundle and the runner imports the bundle on demand.

What's here:

  * ``wire``        — ``/v1/ws/worker`` frames (``make_node_exec``,
                      ``make_missing_dep``, ``binary_install_hint``)
  * ``_logging``    — coloured stdout logger
  * ``ids``         — file id generation (used by output staging)
  * ``config``      — ``DATA_DIR`` / ``SCRATCH_BASE_DIR``
  * ``exceptions``  — ``AppError`` family + ``MissingDependencyError``
  * ``runtime``     — ``run_blocking`` + ``write_text`` (off-event-loop IO
                      helpers)
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from icefold._logging import log_debug, log_error, log_info, log_warning
from icefold.ids import get_file_id
from icefold.runtime import run_blocking, write_text

# Prefer the installed distribution's real version so it can't silently drift
# from a hardcoded literal; fall back when running from an uninstalled checkout.
try:
    __version__ = _pkg_version("icefold-sdk")
except PackageNotFoundError:
    __version__ = "0.1.3"

__all__ = [
    "__version__",
    "log_info",
    "log_warning",
    "log_error",
    "log_debug",
    "get_file_id",
    "run_blocking",
    "write_text",
]
