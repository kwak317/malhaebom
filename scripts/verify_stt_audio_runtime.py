"""Exercise faster-whisper's real audio decoder without downloading a model."""
from io import BytesIO
import wave

import av
from faster_whisper.audio import decode_audio


def main() -> None:
    wav = BytesIO()
    with wave.open(wav, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\0\0" * 16000)
    wav.seek(0)
    decoded = decode_audio(wav, sampling_rate=16000)
    assert decoded.shape == (16000,), decoded.shape
    assert decoded.dtype.name == "float32", decoded.dtype
    try:
        decode_audio(BytesIO(b"invalid WAV"))
    except av.error.InvalidDataError:
        pass
    else:
        raise AssertionError("Invalid audio was accepted")
    print(f"STT audio decoder smoke passed (PyAV {av.__version__})")


if __name__ == "__main__":
    main()
