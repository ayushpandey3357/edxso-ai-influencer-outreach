import pytest
from app.enrichment import EnrichmentService


def test_calculate_engagement_rate_valid():
    video_stats = {
        "vid1": {"views": 10000, "likes": 300, "comments": 100},  # (300+100)/10000 * 100 = 4.0%
        "vid2": {"views": 20000, "likes": 400, "comments": 100},  # (400+100)/20000 * 100 = 2.5%
    }
    rate = EnrichmentService.calculate_engagement_rate(video_stats)
    # Mean of 4.0 and 2.5 = 3.25
    assert rate == 3.25


def test_calculate_engagement_rate_missing_stats():
    video_stats = {}
    rate = EnrichmentService.calculate_engagement_rate(video_stats)
    assert rate == "Not Found"


def test_calculate_engagement_rate_zero_views():
    video_stats = {
        "vid1": {"views": 0, "likes": 0, "comments": 0}
    }
    rate = EnrichmentService.calculate_engagement_rate(video_stats)
    assert rate == "Not Found"
