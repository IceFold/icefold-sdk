"""Data-dir layout the media helpers read.

Everything hangs off ``ICEFOLD_PROJECT_ROOT``: the backend sets it to its
project root; the runner sets it to its ``--work-dir``. So ffmpeg products and
staged files land under whichever process is running the node.
"""

import os

PROJECT_ROOT = os.environ.get("ICEFOLD_PROJECT_ROOT") or os.getcwd()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Where a node writes its product files: ephemeral scratch that the backend
# promotes into the canonical Library store once the run succeeds. Named ``tmp``
# to reflect that — the process running the node (backend or runner) owns it.
TMP_BASE_DIR = os.path.join(DATA_DIR, "tmp")
