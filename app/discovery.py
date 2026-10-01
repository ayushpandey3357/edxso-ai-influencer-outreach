import logging
from typing import List, Dict, Any, Set, Optional
from app.youtube_client import YouTubeClient, MissingAPIKeyError
from app.config import Config

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_QUERIES = [
    "AI tools",
    "artificial intelligence",
    "machine learning",
    "Python programming",
    "data science",
    "software engineering",
    "developer tools",
    "generative AI",
    "coding tutorials",
    "technology",
]


class DiscoveryService:
    """Handles multi-query YouTube channel discovery with pagination and deduplication."""

    def __init__(self, youtube_client: Optional[YouTubeClient] = None):
        self.youtube_client = youtube_client

    def _get_client(self) -> YouTubeClient:
        if not self.youtube_client:
            self.youtube_client = YouTubeClient()
        return self.youtube_client

    def discover_channels(
        self,
        queries: Optional[List[str]] = None,
        target_count: int = Config.TARGET_DISCOVERY_COUNT,
    ) -> List[Dict[str, Any]]:
        """
        Discovers YouTube channels across multiple tech queries.
        Paginates until target_count unique channel IDs are collected.
        Returns list of basic channel records marked as DISCOVERED.
        """
        if not Config.validate_youtube_key():
            raise MissingAPIKeyError(
                "YouTube API Key is missing or default. Cannot perform real channel discovery."
            )

        client = self._get_client()
        search_queries = queries or DEFAULT_SEARCH_QUERIES

        discovered_channels: List[Dict[str, Any]] = []
        seen_channel_ids: Set[str] = set()

        logger.info(f"Starting discovery targeting at least {target_count} unique channels...")

        for query in search_queries:
            if len(seen_channel_ids) >= target_count:
                logger.info(f"Target count {target_count} reached. Stopping query search.")
                break

            logger.info(f"Searching query: '{query}'")
            page_token = None

            # Paginate up to 3 pages per query if target not reached
            for page in range(3):
                if len(seen_channel_ids) >= target_count:
                    break

                response = client.search_channels(
                    query=query, max_results=50, page_token=page_token
                )
                items = response.get("items", [])
                page_token = response.get("nextPageToken")

                added_in_page = 0
                for item in items:
                    id_info = item.get("id", {})
                    channel_id = id_info.get("channelId")
                    if not channel_id:
                        snippet = item.get("snippet", {})
                        channel_id = snippet.get("channelId")

                    if channel_id and channel_id not in seen_channel_ids:
                        seen_channel_ids.add(channel_id)
                        snippet = item.get("snippet", {})
                        record = {
                            "channel_id": channel_id,
                            "name": snippet.get("title") or snippet.get("channelTitle", "Unknown"),
                            "platform": "YouTube",
                            "profile_url": f"https://www.youtube.com/channel/{channel_id}",
                            "channel_description": snippet.get("description", ""),
                            "data_source": "YouTube Data API v3",
                            "filter_status": "DISCOVERED",
                            "filter_reason": "Discovered via YouTube search",
                        }
                        discovered_channels.append(record)
                        added_in_page += 1

                logger.info(
                    f"Query '{query}' Page {page+1}: +{added_in_page} new channels (Total unique: {len(seen_channel_ids)})"
                )

                if not page_token:
                    break

        logger.info(f"Discovery complete. Total unique channels discovered: {len(discovered_channels)}")
        return discovered_channels
