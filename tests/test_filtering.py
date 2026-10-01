import pytest
from app.filtering import FilteringService


def test_micro_influencer_filter_qualified():
    service = FilteringService(min_subscribers=5000, max_subscribers=100000, min_engagement_rate=1.0)
    channels = [
        {
            "name": "AI Tech World",
            "subscriber_count": 25000,
            "engagement_rate": 2.5,
            "content_themes": "AI, Python",
            "channel_description": "Tutorials on Python and artificial intelligence",
            "recent_video_titles": "Building LLMs with Python",
        }
    ]
    results = service.filter_and_classify(channels)
    assert len(results) == 1
    assert results[0]["filter_status"] == "QUALIFIED"
    assert "Subscriber count matched" in results[0]["filter_reason"]
    assert "Engagement rate matched" in results[0]["filter_reason"]


def test_micro_influencer_filter_failed_subscriber_count():
    service = FilteringService(min_subscribers=5000, max_subscribers=100000, min_engagement_rate=1.0)
    channels = [
        {
            "name": "Mega Tech",
            "subscriber_count": 500000,  # > 100k
            "engagement_rate": 3.0,
            "content_themes": "AI",
            "channel_description": "Tech news",
            "recent_video_titles": "AI News",
        },
        {
            "name": "Tiny Dev",
            "subscriber_count": 1000,  # < 5k
            "engagement_rate": 5.0,
            "content_themes": "Programming",
            "channel_description": "Coding logs",
            "recent_video_titles": "My first code",
        }
    ]
    results = service.filter_and_classify(channels)
    assert len(results) == 2
    assert results[0]["filter_status"] == "FAILED"
    assert "outside required range" in results[0]["filter_reason"]
    assert results[1]["filter_status"] == "FAILED"
    assert "outside required range" in results[1]["filter_reason"]


def test_micro_influencer_filter_failed_low_engagement():
    service = FilteringService(min_subscribers=5000, max_subscribers=100000, min_engagement_rate=1.0)
    channels = [
        {
            "name": "Low Engager",
            "subscriber_count": 15000,
            "engagement_rate": 0.4,  # < 1.0%
            "content_themes": "Developer Tools",
            "channel_description": "Coding tips",
            "recent_video_titles": "VSCode extensions",
        }
    ]
    results = service.filter_and_classify(channels)
    assert results[0]["filter_status"] == "FAILED"
    assert "below minimum threshold" in results[0]["filter_reason"]
