import logging
from typing import List, Dict, Any, Tuple
from app.config import Config

logger = logging.getLogger(__name__)


class FilteringService:
    """Dedicated filtering module for Technology / AI / Developer micro-influencers."""

    def __init__(
        self,
        min_subscribers: int = Config.MIN_SUBSCRIBERS,
        max_subscribers: int = Config.MAX_SUBSCRIBERS,
        min_engagement_rate: float = Config.MIN_ENGAGEMENT_RATE,
    ):
        self.min_subscribers = min_subscribers
        self.max_subscribers = max_subscribers
        self.min_engagement_rate = min_engagement_rate

    def filter_and_classify(
        self, enriched_channels: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filters and classifies enriched creators.
        Sets filter_status ('QUALIFIED' or 'FAILED') and detailed filter_reason for EVERY creator.
        Does NOT silently drop creators.
        """
        classified_channels = []

        logger.info(
            f"Filtering creators (Subscribers: {self.min_subscribers}-{self.max_subscribers}, Min Engagement: {self.min_engagement_rate}%)..."
        )

        qualified_count = 0
        failed_count = 0

        for channel in enriched_channels:
            sub_count = channel.get("subscriber_count", 0)
            eng_rate = channel.get("engagement_rate", "Not Found")
            content_themes = channel.get("content_themes", "")
            description = channel.get("channel_description", "")
            recent_titles = channel.get("recent_video_titles", "")

            reasons_passed = []
            reasons_failed = []

            # 1. Subscriber Count Check
            if self.min_subscribers <= sub_count <= self.max_subscribers:
                reasons_passed.append(
                    f"Subscriber count matched threshold ({sub_count:,} within [{self.min_subscribers:,}, {self.max_subscribers:,}])"
                )
            else:
                reasons_failed.append(
                    f"Subscriber count ({sub_count:,}) outside required range [{self.min_subscribers:,}, {self.max_subscribers:,}]"
                )

            # 2. Engagement Rate Check
            if isinstance(eng_rate, (int, float)):
                if eng_rate >= self.min_engagement_rate:
                    reasons_passed.append(
                        f"Engagement rate matched threshold ({eng_rate:.2f}% >= {self.min_engagement_rate}%)"
                    )
                else:
                    reasons_failed.append(
                        f"Engagement rate ({eng_rate:.2f}%) below minimum threshold ({self.min_engagement_rate}%)"
                    )
            else:
                reasons_failed.append(
                    "Engagement rate could not be calculated (Not Found / insufficient public data)"
                )

            # 3. Technology / AI / Developer Relevance Check
            combined_text = (content_themes + " " + description + " " + recent_titles).lower()
            tech_keywords = [
                "ai", "python", "developer", "coding", "software", "machine learning",
                "tech", "programming", "data science", "cloud", "generative"
            ]
            matched_kw = [kw for kw in tech_keywords if kw in combined_text]

            if matched_kw:
                reasons_passed.append(
                    f"Technology relevance detected (keywords matched: {', '.join(matched_kw[:3])})"
                )
            else:
                reasons_failed.append("No technology/AI/developer relevance keywords detected")

            # Final classification logic
            channel_copy = dict(channel)
            if not reasons_failed:
                channel_copy["filter_status"] = "QUALIFIED"
                channel_copy["filter_reason"] = "; ".join(reasons_passed)
                qualified_count += 1
            else:
                channel_copy["filter_status"] = "FAILED"
                channel_copy["filter_reason"] = "; ".join(reasons_failed)
                failed_count += 1

            classified_channels.append(channel_copy)

        logger.info(
            f"Filtering complete. Total: {len(classified_channels)} | QUALIFIED: {qualified_count} | FAILED: {failed_count}"
        )
        return classified_channels
