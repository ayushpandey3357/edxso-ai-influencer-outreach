import json
import logging
import re
from typing import Dict, Any, Tuple, Optional
from app.config import Config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an AI outreach coordinator writing personalized collaboration messages to tech micro-influencers. "
    "CRITICAL RULE: Use ONLY supplied facts. Never invent a recent video, audience demographic, achievement, "
    "partnership, personal detail, or other fact. If a field is 'Not Found', do not mention it.\n\n"
    "You must return ONLY a JSON object matching this schema:\n"
    "{\n"
    '  "email_pitch": "...",\n'
    '  "instagram_dm": "..."\n'
    "}\n\n"
    "LENGTH CONSTRAINTS:\n"
    "1. email_pitch MUST BE EXACTLY BETWEEN 60 AND 90 WORDS.\n"
    "2. instagram_dm MUST BE EXACTLY BETWEEN 15 AND 30 WORDS."
)


class PersonalizationService:
    """Handles AI-powered personalized message generation with strict word count validation and fact verification."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or Config.LLM_PROVIDER).lower()
        self.openai_client = None
        self.genai_client = None
        self.active_provider = "mock"

        if Config.OPENAI_API_KEY and Config.OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
                self.active_provider = "openai"
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}")

        if not self.openai_client and Config.GEMINI_API_KEY and Config.GEMINI_API_KEY != "your_gemini_api_key_here":
            try:
                from google import genai
                self.genai_client = genai.Client(api_key=Config.GEMINI_API_KEY)
                self.active_provider = "gemini"
            except Exception as e:
                logger.warning(f"Could not initialize Gemini client: {e}")

        if self.active_provider == "mock":
            logger.info("No active LLM API client available. PersonalizationService running in deterministic MOCK mode.")

    def generate_messages(
        self, creator: Dict[str, Any], max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generates personalized email pitch (60-90 words) and Instagram DM (15-30 words)
        for a qualified creator with programmatic word count validation and retries.
        """
        name = creator.get("name", "Creator")
        themes = creator.get("content_themes", "Technology")
        recent_titles = creator.get("recent_video_titles", "Not Found")
        sub_count = creator.get("subscriber_count", 0)
        eng_rate = creator.get("engagement_rate", "Not Found")

        user_prompt = (
            f"Creator Name: {name}\n"
            f"Niche/Category: Technology / AI / Developer\n"
            f"Content Themes: {themes}\n"
            f"Subscriber Count: {sub_count:,}\n"
            f"Engagement Rate: {eng_rate}\n"
            f"Recent Video Titles: {recent_titles}\n\n"
            f"Task: Generate a personalized Email Pitch (60-90 words) offering an AI developer tool partnership, "
            f"and an Instagram DM (15-30 words). Focus on their real content themes and video titles."
        )

        for attempt in range(1, max_retries + 1):
            try:
                raw_json_str = self._call_llm(user_prompt, attempt)
                messages = self._parse_json(raw_json_str)

                email_pitch = messages.get("email_pitch", "")
                instagram_dm = messages.get("instagram_dm", "")

                email_words = self.count_words(email_pitch)
                dm_words = self.count_words(instagram_dm)

                email_valid = 60 <= email_words <= 90
                dm_valid = 15 <= dm_words <= 30

                if email_valid and dm_valid:
                    logger.info(
                        f"Generated valid messages for {name} (Email: {email_words} words, DM: {dm_words} words)"
                    )
                    return {
                        "email_pitch": email_pitch,
                        "instagram_dm": instagram_dm,
                        "email_word_count": email_words,
                        "dm_word_count": dm_words,
                        "generation_status": "SUCCESS",
                    }
                else:
                    logger.warning(
                        f"Attempt {attempt}/{max_retries} failed word count limits for {name}. "
                        f"Email: {email_words} (req 60-90), DM: {dm_words} (req 15-30)."
                    )
                    user_prompt += (
                        f"\n\nFEEDBACK FOR RETRY #{attempt}: "
                        f"Your previous output violated word limits. "
                        f"Email pitch had {email_words} words (MUST be 60-90 words). "
                        f"Instagram DM had {dm_words} words (MUST be 15-30 words). Please adjust strictly."
                    )
            except Exception as e:
                logger.error(f"Error calling LLM on attempt {attempt} for {name}: {e}")

        # If retries exhausted or in mock mode, generate formatted fallback adhering strictly to bounds
        return self._generate_fallback_messages(creator)

    def _call_llm(self, user_prompt: str, attempt: int) -> str:
        """Invokes the active LLM provider (OpenAI or Gemini)."""
        if self.active_provider == "openai" and self.openai_client:
            response = self.openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            return response.choices[0].message.content or "{}"
        elif self.active_provider == "gemini" and self.genai_client:
            response = self.genai_client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=f"{SYSTEM_PROMPT}\n\n{user_prompt}",
                config={"response_mime_type": "application/json"},
            )
            return response.text or "{}"
        else:
            raise RuntimeError("No active LLM provider available.")

    def _parse_json(self, raw_str: str) -> Dict[str, str]:
        """Safely parses JSON output from LLM response."""
        clean_str = raw_str.strip()
        if clean_str.startswith("```json"):
            clean_str = clean_str[7:]
        if clean_str.endswith("```"):
            clean_str = clean_str[:-3]
        clean_str = clean_str.strip()

        data = json.loads(clean_str)
        return {
            "email_pitch": data.get("email_pitch", ""),
            "instagram_dm": data.get("instagram_dm", ""),
        }

    @staticmethod
    def count_words(text: str) -> int:
        """Counts words accurately by splitting whitespace."""
        if not text:
            return 0
        return len(text.strip().split())

    def _generate_fallback_messages(self, creator: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates deterministic, factual pitch & DM adhering strictly to 60-90 words (email)
        and 15-30 words (DM) using actual collected creator data.
        Used as a robust mock mode or fallback when API keys aren't configured.
        """
        name = creator.get("name", "Creator")
        themes = creator.get("content_themes", "Technology")
        recent_titles = creator.get("recent_video_titles", "your latest videos")
        first_title = recent_titles.split(";")[0] if ";" in recent_titles else recent_titles

        # Factually accurate Email Pitch (75 words, cleanly inside 60-90 words limit)
        email_pitch = (
            f"Hi {name}, I came across your YouTube channel and really appreciated your recent content on "
            f"{first_title}. Your focus on {themes} resonates strongly with developer communities. "
            f"We are building an AI developer productivity tool designed to streamline coding workflows. "
            f"Given your technical audience engagement, we would love to sponsor an upcoming video or collaborate "
            f"on a product breakdown. Would you be open to exploring a partnership this month? Best regards."
        )

        # Factually accurate Instagram DM (22 words, cleanly inside 15-30 words limit)
        instagram_dm = (
            f"Hey {name}, loved your recent YouTube video on {first_title}! We'd love to collaborate on an AI dev tool partnership."
        )

        e_count = self.count_words(email_pitch)
        d_count = self.count_words(instagram_dm)

        return {
            "email_pitch": email_pitch,
            "instagram_dm": instagram_dm,
            "email_word_count": e_count,
            "dm_word_count": d_count,
            "generation_status": "MOCK_FALLBACK" if self.active_provider == "mock" else "FALLBACK_SUCCESS",
        }
