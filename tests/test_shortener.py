import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.shortener import code_for_id, decode, encode


def test_encode_decode_roundtrip():
    for n in [0, 1, 61, 62, 12345, 999_999_999]:
        assert decode(encode(n)) == n


def test_codes_are_unique_per_id():
    codes = {code_for_id(i) for i in range(1, 5000)}
    assert len(codes) == 4999  # no collisions


def test_codes_are_short_and_alphanumeric():
    c = code_for_id(1)
    assert c.isalnum() and 1 <= len(c) <= 8
