"""Approximate raw-score -> scaled-score conversion for mock exam mode.

TOEIC's real conversion tables are proprietary and vary slightly between
test administrations, so this uses a simple proportional approximation
against the public 5-495 per-section / 10-990 total scale, rounded to the
nearest multiple of 5 (as real TOEIC scaled scores always are). This is
clearly surfaced to the user as a reference estimate, not an official score.
"""

TOEIC_SECTION_MIN = 5
TOEIC_SECTION_MAX = 495


def toeic_scaled_score(raw_correct: int, raw_total: int) -> int:
    """Approximate a TOEIC Listening or Reading scaled score (5-495, in
    multiples of 5) from a raw correct-answer count.
    """
    if raw_total <= 0:
        return TOEIC_SECTION_MIN
    pct = max(0.0, min(1.0, raw_correct / raw_total))
    scaled = TOEIC_SECTION_MIN + pct * (TOEIC_SECTION_MAX - TOEIC_SECTION_MIN)
    scaled = round(scaled / 5) * 5
    return int(max(TOEIC_SECTION_MIN, min(TOEIC_SECTION_MAX, scaled)))
