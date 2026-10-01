import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Union
from app.youtube_client import YouTubeClient
from app.config import Config

logger = logging.getLogger(__name__)

# Strict Email Regex: extracts explicitly listed email addresses
EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE
)

# Defined Content Themes
THEME_KEYWORDS = {
    "AI": [r"\bai\b", r"artificial intelligence", r"llm", r"gpt", r"claude", r"neural network"],
    "Machine Learning": [r"machine learning", r"\bml\b", r"deep learning", r"scikit", r"pytorch", r"tensorflow"],
    "Python": [r"python", r"django", r"fastapi", r"flask", r"pandas", r"numpy"],
    "Programming": [r"programming", r"coding", r"code", r"developer", r"algorithm"],
    "Data Science": [r"data science", r"data analyst", r"data engineering", r"big data"],
    "Generative AI": [r"generative ai", r"genai", r"stable diffusion", r"midjourney", r"prompt engineering"],
    "Developer Tools": [r"developer tool", r"devtools", r"vscode", r"git", r"docker", r"kubernetes"],
    "Cloud": [r"cloud", r"aws", r"azure", r"gcp", r"google cloud"],
    "Software Engineering": [r"software engineer", r"software development", r"architecture", r"system design"],
    "Technology": [r"technology", r"tech", r"gadgets", r"software"],
}


class EnrichmentService:
    """Enriches discovered YouTube channels with statistics, recent video stats, email extraction, engagement rate, and content themes."""

    def __init__(self, youtube_client: Optional[YouTubeClient] = None):
        self.youtube_client = youtube_client

    def _get_client(self) -> YouTubeClient:
        if not self.youtube_client:
            self.youtube_client = YouTubeClient()
        return self.youtube_client

    def enrich_channels(
        self, discovered_channels: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Takes raw discovered channels and collects detailed profile metrics,
        recent video statistics, email, engagement rate, and content themes.
        """
        if not discovered_channels:
            return []

        client = self._get_client()
        channel_ids = [c["channel_id"] for c in discovered_channels]

        logger.info(f"Enriching details for {len(channel_ids)} channels...")
        channels_details = client.get_channels_details(channel_ids)
        details_by_id = {item["id"]: item for item in channels_details}

        enriched_list = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for raw_channel in discovered_channels:
            c_id = raw_channel["channel_id"]
            detail = details_by_id.get(c_id, {})

            snippet = detail.get("snippet", {})
            statistics = detail.get("statistics", {})
            content_details = detail.get("contentDetails", {})

            subscriber_count = int(statistics.get("subscriberCount", 0))
            video_count = int(statistics.get("videoCount", 0))
            view_count = int(statistics.get("viewCount", 0))
            description = snippet.get("description") or raw_channel.get("channel_description", "")
            channel_name = snippet.get("title") or raw_channel.get("name", "Unknown Channel")

            # Fetch recent videos via uploads playlist
            uploads_playlist_id = content_details.get("relatedPlaylists", {}).get("uploads", "")
            recent_video_titles = []
            recent_video_descriptions = []
            video_ids = []

            if uploads_playlist_id:
                playlist_items = client.get_recent_videos_for_playlist(
                    uploads_playlist_id, max_results=Config.RECENT_VIDEO_COUNT
                )
                for item in playlist_items:
                    v_snippet = item.get("snippet", {})
                    v_id = v_snippet.get("resourceId", {}).get("videoId")
                    if v_id:
                        video_ids.append(v_id)
                        recent_video_titles.append(v_snippet.get("title", ""))
                        recent_video_descriptions.append(v_snippet.get("description", ""))

            # Fetch video statistics (views, likes, comments)
            video_stats_dict = client.get_video_statistics(video_ids) if video_ids else {}

            # Calculate Engagement Rate
            engagement_rate = self.calculate_engagement_rate(video_stats_dict)

            # Extract Email (strict regex only)
            combined_text_for_email = description + " " + " ".join(recent_video_descriptions)
            contact_email = self.extract_email(combined_text_for_email)

            # Detect Content Themes
            combined_text_for_themes = (channel_name + " " + description + " " + " ".join(recent_video_titles)).lower()
            content_themes = self.detect_content_themes(combined_text_for_themes)

            record = {
                "name": channel_name,
                "platform": "YouTube",
                "channel_id": c_id,
                "profile_url": f"https://www.youtube.com/channel/{c_id}",
                "subscriber_count": subscriber_count,
                "channel_description": description,
                "video_count": video_count,
                "view_count": view_count,
                "recent_video_titles": "; ".join(recent_video_titles) if recent_video_titles else "Not Found",
                "data_source": "YouTube Data API v3",
                "data_collected_at": now_iso,
                "engagement_rate": engagement_rate,
                "contact_email": contact_email,
                "category_niche": "Technology / AI / Developer",
                "content_themes": ", ".join(content_themes) if content_themes else "Technology",
                "website": "Not Found",
                "audience_age": "Not Found",
                "audience_gender": "Not Found",
                "audience_geography": "Not Found",
                "filter_status": raw_channel.get("filter_status", "DISCOVERED"),
                "filter_reason": raw_channel.get("filter_reason", "Discovered"),
            }
            enriched_list.append(record)

        logger.info(f"Enrichment completed for {len(enriched_list)} channels.")
        return enriched_list

    @staticmethod
    def calculate_engagement_rate(
        video_stats_dict: Dict[str, Dict[str, Any]]
    ) -> Union[float, str]:
        """
        Calculates mean engagement rate = (likes + comments) / views * 100
        across available recent videos.
        Returns float (e.g. 2.45) or 'Not Found'.
        """
        if not video_stats_dict:
            return "Not Found"

        rates = []
        for v_id, stats in video_stats_dict.items():
            views = stats.get("views", 0)
            likes = stats.get("likes", 0)
            comments = stats.get("comments", 0)

            if views > 0:
                rate = ((likes + comments) / views) * 100.0
                rates.append(rate)

        if not rates:
            return "Not Found"

        mean_rate = sum(rates) / len(rates)
        return round(mean_rate, 2)

    @staticmethod
    def extract_email(text: str) -> str:
        """
        Extracts an explicitly present email from text using regex.
        Strict rule: Never guess an email. Returns 'Not Found' if missing.
        """
        if not text:
            return "Not Found"

        matches = EMAIL_REGEX.findall(text)
        for match in matches:
            # Filter out non-email domain artifacts or image extension matches if any
            email_candidate = match.strip().lower()
            if not any(email_candidate.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".svg"]):
                return email_candidate

        return "Not Found"

    @staticmethod
    def detect_content_themes(text: str) -> List[str]:
        """
        Determines matching content themes based on keyword evidence in channel text.
        """
        detected = []
        for theme, keywords in THEME_KEYWORDS.items():
            for kw in keywords:
                if re.search(kw, text, re.IGNORECASE):
                    detected.append(theme)
                    break
        return detected
