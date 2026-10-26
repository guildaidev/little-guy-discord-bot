import random
import re
import sqlite3
from datetime import date, datetime
from datetime import time


EXECUTION_REQUEST = re.compile(
    r"\b(?:please\s+|(?:can|could|would|will)\s+you\s+(?:please\s+)?)"
    r"(?:actually\s+)?(?:run|execut\w*|launch|deploy|compile|eval(?:uate)?|install)\b"
    r"|\b(?:run|execut\w*|launch|deploy|compile|eval(?:uate)?|install)\b"
    r".{0,30}\b(?:this|that|my|the attached|the following)\b"
    r".{0,30}\b(?:code|script|command|program)\b",
    re.IGNORECASE | re.DOTALL,
)

SILENCE_REQUEST = re.compile(
    r"\b(?:shut\s+up|stop\s+(?:talking|speaking|replying|responding)|"
    r"be\s+quiet|go\s+away|leave\s+me\s+alone|nobody\s+asked|"
    r"bad\s+bot|you\s+suck|i\s+hate\s+(?:you|this)|"
    r"you(?:'re|\s+are)\s+(?:stupid|dumb|useless|annoying|awful|terrible)|"
    r"(?:(?:that|this|your)\s+(?:answer|response)|that|this)\s+(?:is|was)\s+"
    r"(?:stupid|dumb|useless|annoying|awful|terrible|bad|wrong)|"
    r"(?:that|this)\s+(?:didn'?t|doesn'?t)\s+help|"
    r"(?:not|wasn'?t|isn'?t)\s+(?:useful|helpful))\b",
    re.IGNORECASE,
)

GREETER_MESSAGE = re.compile(
    r"^Hey\s+<@!?(\d+)>!\s+We\s+are\s+so\s+glad\s+you\s+joined\s+"
    r"\*\*Guild\.AI(?:!)?\*\*(?:!)?"
    r"(?:\r?\nhttps://i\.imgur\.com/PCTYgeY\.gif)?$",
    re.IGNORECASE,
)

WEB_SEARCH_REQUEST = re.compile(
    r"\b(?:search(?:\s+the)?\s+web|look\s+it\s+up|look\s+up|google|"
    r"browse|find\s+(?:online|on\s+the\s+web)|latest|current(?:ly)?|"
    r"today|recent(?:ly)?|news|verify|fact[- ]check|source(?:s)?)\b",
    re.IGNORECASE,
)

BLOCKED_SEARCH_TOPIC = re.compile(
    r"\b(?:nsfw|porn(?:ography|ographic)?|explicit\s+sexual|sexual\s+content|"
    r"nudes?|erotic(?:a)?|fetish|adult\s+content|"
    r"politics?|political|elections?|campaign(?:ing)?|partisan|"
    r"democrats?|republicans?|congress|senate|parliament|geopolitics?|"
    r"state\s+of\s+the\s+world|world\s+affairs|global\s+affairs|"
    r"international\s+conflicts?|culture\s+wars?)\b",
    re.IGNORECASE,
)


def requests_code_execution(text: str) -> bool:
    return bool(EXECUTION_REQUEST.search(text))


def requests_silence(text: str) -> bool:
    return bool(SILENCE_REQUEST.search(text))


def should_use_discord_reply(text: str) -> bool:
    return "?" in text


def requires_web_search(text: str) -> bool:
    return bool(WEB_SEARCH_REQUEST.search(text))


def is_blocked_search_topic(text: str) -> bool:
    return bool(BLOCKED_SEARCH_TOPIC.search(text))


def greeter_member_id(text: str) -> int | None:
    match = GREETER_MESSAGE.fullmatch(text.strip())
    return int(match.group(1)) if match else None


def sentence_count(text: str) -> int:
    chunks = [part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part]
    return len(chunks)


def parse_discussion_window(start_hour: str, end_hour: str) -> tuple[int, int]:
    # The window runs from start_hour:00 up to, but not including, end_hour:00.
    try:
        start, end = int(start_hour), int(end_hour)
    except ValueError as error:
        raise RuntimeError("DISCUSSION_START_HOUR and DISCUSSION_END_HOUR must be whole hours.") from error
    if not 0 <= start < end <= 24:
        raise RuntimeError("Discussion prompt hours must satisfy 0 <= DISCUSSION_START_HOUR < DISCUSSION_END_HOUR <= 24.")
    return start, end


def random_allowed_time(
    start_hour: int,
    end_hour: int,
    rng: random.Random | None = None,
) -> time:
    source = rng or random.SystemRandom()
    minute = source.randrange(start_hour * 60, end_hour * 60)
    return time(hour=minute // 60, minute=minute % 60)


def is_allowed_time(value: time, start_hour: int, end_hour: int) -> bool:
    return start_hour <= value.hour < end_hour


def prompt_sent_on(
    database: sqlite3.Connection,
    guild_id: int,
    local_day: date,
) -> bool:
    row = database.execute(
        "SELECT 1 FROM discussion_runs WHERE guild_id = ? AND local_date = ?",
        (guild_id, local_day.isoformat()),
    ).fetchone()
    return row is not None


def record_prompt_send(
    database: sqlite3.Connection,
    guild_id: int,
    local_day: date,
    source: str,
    sent_at: datetime,
):
    database.execute(
        "INSERT INTO discussion_runs (guild_id, local_date, source, sent_at) "
        "VALUES (?, ?, ?, ?)",
        (guild_id, local_day.isoformat(), source, sent_at.isoformat()),
    )
    database.commit()
