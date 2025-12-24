import functools
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BeforeValidator,
)

from radiofeed.episodes.models import Episode
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers.validators import (
    default_if_none,
    is_one_of,
    normalize_url,
    one_of_choices,
    pg_integer,
)

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


OptionalUrl = Annotated[str | None, AfterValidator(normalize_url)]

PgInteger = Annotated[int | None, BeforeValidator(pg_integer)]

Explicit = Annotated[
    bool,
    BeforeValidator(
        functools.partial(is_one_of, values=("clean", "yes", "true")),
    ),
]

EmptyIfNone = Annotated[
    str, BeforeValidator(functools.partial(default_if_none, default=""))
]

EpisodeType = Annotated[
    str,
    BeforeValidator(
        functools.partial(
            one_of_choices,
            choices=Episode.EpisodeType,
            default=Episode.EpisodeType.FULL,
        )
    ),
]

PodcastType = Annotated[
    str,
    BeforeValidator(
        functools.partial(
            one_of_choices,
            choices=Podcast.PodcastType,
            default=Podcast.PodcastType.EPISODIC,
        )
    ),
]
