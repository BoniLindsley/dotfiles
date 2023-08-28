#!/usr/bin/env python3

# Standard libraries.
import json
import queue
import sys

# External dependencies.
import sounddevice
import vosk


def main() -> int:
    audio_input: queue.Queue[bytes] = queue.Queue()

    def callback(indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        del frames
        del status
        del time
        audio_input.put(bytes(indata))

    device_info = sounddevice.query_devices(kind="input")
    sample_rate = int(device_info["default_samplerate"])

    model = vosk.Model(lang="en-us")
    with sounddevice.RawInputStream(
        samplerate=sample_rate,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        rec = vosk.KaldiRecognizer(model, sample_rate)
        try:
            while True:
                data = audio_input.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    print(result["text"], end="...\n< ")
                else:
                    result = json.loads(rec.PartialResult())
                    print(result["partial"], end="...\r< ")
        except KeyboardInterrupt:
            return 2


if __name__ == "__main__":
    sys.exit(main())
