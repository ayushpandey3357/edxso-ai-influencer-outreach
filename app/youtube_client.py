import logging
from typing import Dict, List, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import Config

logger = logging.getLogger(__name__)


class YouTubeAPIError(Exception):
    """Base exception for YouTube API errors."""
    pass


class MissingAPIKeyError(YouTubeAPIError):
    """Raised when YouTube API key is missing."""
    pass


class QuotaExceededError(YouTubeAPIError):
    """Raised when YouTube API quota is exceeded."""
    pass


class YouTubeClient:
    """Wrapper around official YouTube Data API v3 client."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.YOUTUBE_API_KEY
        if not self.api_key or self.api_key == "your_youtube_api_key_here":
            raise MissingAPIKeyError(
                "YouTube API key is missing. Please set YOUTUBE_API_KEY in your .env file."
            )
        try:
            self.youtube = build("youtube", "v3", developerKey=self.api_key)
        except Exception as e:
            raise YouTubeAPIError(f"Failed to initialize YouTube API client: {e}")

    def search_channels(
        self, query: str, max_results: int = 50, page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Searches YouTube for channels matching a search query.
        Returns raw API response including items and nextPageToken.
        """
        try:
            request = self.youtube.search().list(
                q=query,
                type="channel",
                part="snippet",
                maxResults=min(max_results, 50),
                pageToken=page_token,
            )
            response = request.execute()
            return response
        except HttpError as e:
            self._handle_http_error(e)
            return {}

    def get_channels_details(self, channel_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetches channel snippet, statistics, and contentDetails for a list of channel IDs.
        Batches requests in chunks of 50.
        """
        if not channel_ids:
            return []

        all_channels = []
        chunk_size = 50

        for i in range(0, len(channel_ids), chunk_size):
            chunk = channel_ids[i:i + chunk_size]
            try:
                request = self.youtube.channels().list(
                    id=",".join(chunk),
                    part="snippet,statistics,contentDetails",
                    maxResults=50,
                )
                response = request.execute()
                all_channels.extend(response.get("items", []))
            except HttpError as e:
                self._handle_http_error(e)

        return all_channels

    def get_recent_videos_for_playlist(
        self, uploads_playlist_id: str, max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fetches recent video items from a channel's uploads playlist.
        """
        if not uploads_playlist_id:
            return []

        try:
            request = self.youtube.playlistItems().list(
                playlistId=uploads_playlist_id,
                part="snippet",
                maxResults=max_results,
            )
            response = request.execute()
            return response.get("items", [])
        except HttpError as e:
            logger.warning(f"Failed to fetch playlist items for {uploads_playlist_id}: {e}")
            return []

    def get_video_statistics(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetches statistics (views, likes, comments) and snippets for a list of video IDs.
        Returns a dict mapping video_id to stats.
        """
        if not video_ids:
            return {}

        results = {}
        chunk_size = 50

        for i in range(0, len(video_ids), chunk_size):
            chunk = video_ids[i:i + chunk_size]
            try:
                request = self.youtube.videos().list(
                    id=",".join(chunk),
                    part="snippet,statistics",
                    maxResults=50,
                )
                response = request.execute()
                for item in response.get("items", []):
                    v_id = item.get("id")
                    stats = item.get("statistics", {})
                    snippet = item.get("snippet", {})
                    results[v_id] = {
                        "video_id": v_id,
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                    }
            except HttpError as e:
                logger.warning(f"Failed to fetch video statistics: {e}")

        return results

    def _handle_http_error(self, error: HttpError):
        """Processes HTTP errors and raises specific exceptions when applicable."""
        error_msg = str(error)
        if error.resp.status == 403 and "quotaExceeded" in error_msg:
            raise QuotaExceededError("YouTube API quota exceeded for today.")
        elif error.resp.status == 403:
            raise YouTubeAPIError(f"YouTube API permission error / key invalid: {error}")
        else:
            raise YouTubeAPIError(f"YouTube API HTTP error ({error.resp.status}): {error}")
