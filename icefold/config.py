"""Data-dir layout the media helpers read.

Everything hangs off ``ICEFOLD_PROJECT_ROOT``: the backend sets it to its
project root; the runner sets it to its ``--work-dir``. So ffmpeg products and
staged files land under whichever process is running the node.
"""

import os

PROJECT_ROOT = os.environ.get("ICEFOLD_PROJECT_ROOT") or os.getcwd()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

UPLOAD_BASE_DIR = os.path.join(DATA_DIR, "upload")
DOWNLOAD_BASE_DIR = os.path.join(DATA_DIR, "download")
