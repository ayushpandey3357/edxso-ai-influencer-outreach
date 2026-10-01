import pytest
from app.personalization import PersonalizationService


def test_word_count_helper():
    text = "  This is   a test of word count calculation.  "
    assert PersonalizationService.count_words(text) == 8


def test_fallback_message_word_counts():
    service = PersonalizationService(provider="mock")
    creator = {
        "name": "Dev Channel",
        "content_themes": "Python, AI",
        "recent_video_titles": "Building LLM Agents in Python",
        "subscriber_count": 12000,
        "engagement_rate": 3.5,
    }
    messages = service.generate_messages(creator)

    email_pitch = messages["email_pitch"]
    instagram_dm = messages["instagram_dm"]

    e_words = PersonalizationService.count_words(email_pitch)
    d_words = PersonalizationService.count_words(instagram_dm)

    # Email pitch must be strictly between 60 and 90 words
    assert 60 <= e_words <= 90, f"Email pitch word count {e_words} is outside [60, 90]"

    # Instagram DM must be strictly between 15 and 30 words
    assert 15 <= d_words <= 30, f"Instagram DM word count {d_words} is outside [15, 30]"
