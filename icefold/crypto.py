"""Lightweight XOR keystream for the worker WebSocket data channel.

Every JSON frame on the ``/v1/ws/worker`` link is XOR'd with a repeating key
derived from the shared worker auth token. This is *obfuscation*, not
encryption — TLS (wss://) is still the only thing that protects against a
passive listener — but it stops a casual observer from reading message types
and node payloads as plain text, and forces both ends to agree on a shared
secret before exchanging any data.

Layout on the wire:
  * key non-empty → binary WS frames: ``ciphertext = plaintext XOR key*``
  * key empty     → text WS frames with plain JSON (dev / no-auth fallback)
"""

from __future__ import annotations


def xor_bytes(data: bytes, key: bytes) -> bytes:
    """Return ``data`` XOR'd with ``key`` repeated to cover its length.

    An empty key returns ``data`` unchanged so callers can opt out of the
    transform by passing ``b""`` — keeps the fallback path branchless.
    """
    if not key:
        return data
    n = len(key)
    return bytes(b ^ key[i % n] for i, b in enumerate(data))


if __name__ == "__main__":
    assert xor_bytes(b"", b"k") == b""
    assert xor_bytes(b"hi", b"") == b"hi"

    key = b"icefold-worker"
    msg = b'{"type":"hello","worker_id":"w1"}'
    enc = xor_bytes(msg, key)
    assert enc != msg
    assert xor_bytes(enc, key) == msg

    long_msg = msg * 17
    assert xor_bytes(xor_bytes(long_msg, key), key) == long_msg

    utf = "你好，世界".encode("utf-8")
    assert xor_bytes(xor_bytes(utf, key), key) == utf

    print("crypto: OK")
