#!/usr/bin/env python3
"""Bounded newline-delimited JSON frames."""

# Standard libraries.
import json
import typing

from typing import Dict, List

MAX_FRAME = 1024 * 1024


def encode(message: Dict[str, typing.Any]) -> bytes:
    frame = json.dumps(message, allow_nan=False).encode("utf-8") + b"\n"
    if len(frame) > MAX_FRAME:
        raise ValueError("Message exceeds frame limit")
    return frame


def decode(frame: bytes) -> Dict[str, typing.Any]:
    if len(frame) > MAX_FRAME:
        raise ValueError("Message exceeds frame limit")
    message = json.loads(frame.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("Message must be a JSON object")
    return typing.cast(Dict[str, typing.Any], message)


class Decoder:
    def __init__(self) -> None:
        self.buffer = b""

    def feed(self, chunk: bytes) -> List[Dict[str, typing.Any]]:
        self.buffer += chunk
        frames = []
        while b"\n" in self.buffer:
            frame, self.buffer = self.buffer.split(b"\n", 1)
            frames.append(decode(frame + b"\n"))
        if len(self.buffer) >= MAX_FRAME:
            raise ValueError("Message exceeds frame limit")
        return frames
