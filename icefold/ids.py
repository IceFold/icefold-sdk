from ulid import ULID
from uuid_utils import uuid7


def get_file_id() -> str:
    """UUID v7 (time-ordered)."""
    return str(uuid7())


def get_session_id() -> str:
    """Monotonic ULID (lexicographically sortable)."""
    return str(ULID())


def get_event_ulid() -> str:
    """Monotonic ULID for append-only event rows.

    Gives every row a sortable, globally-unique handle so callers can page
    by ULID rather than relying on an integer surrogate key.
    """
    return str(ULID())


if __name__ == "__main__":
    a, b = get_file_id(), get_file_id()
    assert a and b and a != b
    assert len(a) == 36 and a.count("-") == 4, f"file id not uuid-shaped: {a!r}"

    s1, s2 = get_session_id(), get_session_id()
    assert s1 and s2 and s1 != s2
    assert len(s1) == 26, f"session id not ULID-shaped: {s1!r}"

    seq = [get_session_id() for _ in range(5)]
    assert seq == sorted(seq), f"session ids not monotonic: {seq}"

    eseq = [get_event_ulid() for _ in range(5)]
    assert all(len(e) == 26 for e in eseq)
    assert eseq == sorted(eseq), f"event ulids not monotonic: {eseq}"

    print("ids: OK")
