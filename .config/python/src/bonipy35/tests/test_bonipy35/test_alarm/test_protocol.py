#!/usr/bin/env python3

# External dependencies.
import pytest

# Internal modules.
from bonipy35.alarm.protocol import Decoder, MAX_FRAME, decode, encode


class TestFrames:
    def test_fragmented_utf8_and_coalesced_frames(self) -> None:
        frame = encode({"name": "⏰"})
        decoder = Decoder()
        assert not decoder.feed(frame[:2])
        assert not decoder.feed(frame[2:-1])
        assert decoder.feed(frame[-1:] + encode({"id_": 1})) == [
            {"name": "⏰"},
            {"id_": 1},
        ]
        assert decoder.buffer == b""

    @pytest.mark.parametrize(
        "frame", [b"[]\n", b"invalid\n", b"\xff\n", b"x" * (MAX_FRAME + 1)]
    )
    def test_invalid_frame(self, frame: bytes) -> None:
        with pytest.raises(ValueError):
            decode(frame)

    def test_encode_limit_and_nan(self) -> None:
        with pytest.raises(ValueError, match="limit"):
            encode({"value": "x" * MAX_FRAME})
        with pytest.raises(ValueError):
            encode({"value": float("nan")})

    def test_unterminated_frame_limit(self) -> None:
        with pytest.raises(ValueError, match="limit"):
            Decoder().feed(b"x" * MAX_FRAME)
