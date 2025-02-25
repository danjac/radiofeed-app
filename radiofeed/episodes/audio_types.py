from typing import Final, Literal

AudioMimetype = Literal[
    "audio/aac",
    "audio/aacp",
    "audio/basic",
    "audio/L24",  # Assuming PCM 24-bit WAV-like format
    "audio/m4a",
    "audio/midi",
    "audio/mp3",
    "audio/mp4",
    "audio/mp4a-latm",
    "audio/mpef",
    "audio/mpeg",
    "audio/mpeg3",
    "audio/mpeg4",
    "audio/mpg",
    "audio/ogg",
    "audio/video",  # Not a common audio type, assuming default
    "audio/vnd.dlna.adts",
    "audio/vnd.rn-realaudio",  # RealAudio varies, assuming standard quality
    "audio/vnd.wave",
    "audio/vorbis",
    "audio/wav",
    "audio/wave",
    "audio/webm",
    "audio/x-aac",
    "audio/x-aiff",
    "audio/x-flac",
    "audio/x-hx-aac-adts",
    "audio/x-m4a",
    "audio/x-m4b",
    "audio/x-m4v",  # Assuming similar to M4A
    "audio/x-mov",  # Assuming similar to M4A
    "audio/x-mp3",
    "audio/x-mpeg",
    "audio/x-mpg",
    "audio/x-ms-wma",
    "audio/x-pn-realaudio",
    "audio/x-wav",
]

_AUDIO_BITRATES: Final = {
    "audio/aac": 128,
    "audio/aacp": 128,
    "audio/basic": 64,
    "audio/L24": 1411,  # Assuming PCM 24-bit WAV-like format
    "audio/m4a": 128,
    "audio/midi": 32,
    "audio/mp3": 128,
    "audio/mp4": 128,
    "audio/mp4a-latm": 128,
    "audio/mpef": 128,
    "audio/mpeg": 128,
    "audio/mpeg3": 128,
    "audio/mpeg4": 128,
    "audio/mpg": 128,
    "audio/ogg": 96,
    "audio/video": 128,  # Not a common audio type, assuming default
    "audio/vnd.dlna.adts": 128,
    "audio/vnd.rn-realaudio": 96,  # RealAudio varies, assuming standard quality
    "audio/vnd.wave": 1411,
    "audio/vorbis": 96,
    "audio/wav": 1411,
    "audio/wave": 1411,
    "audio/webm": 128,
    "audio/x-aac": 128,
    "audio/x-aiff": 1411,
    "audio/x-flac": 700,
    "audio/x-hx-aac-adts": 128,
    "audio/x-m4a": 128,
    "audio/x-m4b": 128,
    "audio/x-m4v": 128,  # Assuming similar to M4A
    "audio/x-mov": 128,  # Assuming similar to M4A
    "audio/x-mp3": 128,
    "audio/x-mpeg": 128,
    "audio/x-mpg": 128,
    "audio/x-ms-wma": 96,
    "audio/x-pn-realaudio": 96,
    "audio/x-wav": 1411,
}


def get_bitrate(media_type: AudioMimetype, default: int = 128) -> int:
    """Return the bitrate in kPps for the given audio media type."""
    return _AUDIO_BITRATES.get(media_type, default)
