"""Base62 encoding for short codes.

Short codes are the base62 encoding of the row's database id (plus an offset so
codes aren't 1-2 chars). Deriving the code from a unique primary key means codes
are collision-free by construction — no random generation + retry loop needed.
"""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)
OFFSET = 1_000_000  # so id=1 doesn't become a 1-char code


def encode(n: int) -> str:
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return ALPHABET[0]
    out = []
    while n > 0:
        n, rem = divmod(n, BASE)
        out.append(ALPHABET[rem])
    return "".join(reversed(out))


def decode(code: str) -> int:
    n = 0
    for ch in code:
        n = n * BASE + ALPHABET.index(ch)
    return n


def code_for_id(row_id: int) -> str:
    return encode(row_id + OFFSET)
