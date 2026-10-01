import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import Config
from app.discovery import DiscoveryService
from app.enrichment import EnrichmentService
from app.filtering import FilteringService
from app.personalization import PersonalizationService
from app.outreach import OutreachService
from app.db import DatabaseManager

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrates the 7-stage automated micro-influencer discovery, enrichment, filtering, AI personalization, and outreach pipeline."""

    def __init__(
        self,
        discovery_service: Optional[DiscoveryService] = None,
        enrichment_service: Optional[EnrichmentService] = None,
        filtering_service: Optional[FilteringService] = None,
        personalization_service: Optional[PersonalizationService] = None,
        outreach_service: Optional[OutreachService] = None,
        data_dir: Optional[Path] = None,
    ):
        self.discovery_service = discovery_service or DiscoveryService()
        self.enrichment_service = enrichment_service or EnrichmentService()
        self.filtering_service = filtering_service or FilteringService()
        self.personalization_service = personalization_service or PersonalizationService()
        self.outreach_service = outreach_service or OutreachService()
        self.data_dir = data_dir or Config.DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def run(self, target_discovery_count: int = Config.TARGET_DISCOVERY_COUNT) -> Dict[str, Any]:
        """Runs all 7 stages of the pipeline sequentially."""
        print("=" * 60)
        print(" AUTOMATED MICRO-INFLUENCER OUTREACH PIPELINE ")
        print("=" * 60)

        # Stage 1: Discovery
        print("\n[1/7] Discovering creators...")
        discovered = self.discovery_service.discover_channels(target_count=target_discovery_count)
        print(f"Discovered: {len(discovered)} unique channels")

        # Stage 2: Data Collection & Enrichment
        print("\n[2/7] Enriching profiles...")
        enriched = self.enrichment_service.enrich_channels(discovered)
        print(f"Records saved: {len(enriched)}")
        self._export_csv(enriched, self.data_dir / "influencers.csv")

        # Stage 3: Filtering & Classification
        print("\n[3/7] Filtering...")
        classified = self.filtering_service.filter_and_classify(enriched)
        qualified = [c for c in classified if c.get("filter_status") == "QUALIFIED"]
        failed = [c for c in classified if c.get("filter_status") == "FAILED"]
        print(f"Total Classified: {len(classified)} | Qualified: {len(qualified)} | Failed: {len(failed)}")
        self._export_csv(classified, self.data_dir / "classified_influencers.csv")
        self._export_csv(qualified, self.data_dir / "qualified_influencers.csv")

        # Stage 4: AI Personalization
        print("\n[4/7] Generating AI messages...")
        personalized = []
        for creator in qualified:
            msg_data = self.personalization_service.generate_messages(creator)
            merged = dict(creator)
            merged["email_pitch"] = msg_data.get("email_pitch", "")
            merged["instagram_dm"] = msg_data.get("instagram_dm", "")
            merged["email_word_count"] = msg_data.get("email_word_count", 0)
            merged["dm_word_count"] = msg_data.get("dm_word_count", 0)
            personalized.append(merged)
        print(f"Generated personalized messages for {len(personalized)} qualified creators")
        self._export_csv(personalized, self.data_dir / "personalized_outreach.csv")

        # Stage 5 & 6: Database & Sending Simulation
        print("\n[5/7] Creating tracker & checking database duplicates...")
        print("[6/7] Simulating sending...")
        outreach_results = self.outreach_service.process_outreach(personalized)
        simulated_count = sum(1 for r in outreach_results if r.get("sending_status") == "SIMULATED")
        skipped_email_count = sum(1 for r in outreach_results if r.get("sending_status") == "SKIPPED_NO_EMAIL")
        skipped_dup_count = sum(1 for r in outreach_results if r.get("sending_status") == "SKIPPED_DUPLICATE")
        print(
            f"Simulated Send Summary -> Sent: {simulated_count} | Skipped (No Email): {skipped_email_count} | Skipped (Duplicate): {skipped_dup_count}"
        )

        # Stage 7: Export Final Tracker CSV
        print("\n[7/7] Exporting tracker...")
        tracker_formatted = self._format_tracker_output(outreach_results)
        self._export_csv(tracker_formatted, self.data_dir / "outreach_tracker.csv")
        print(f"Exported final tracker to {self.data_dir / 'outreach_tracker.csv'}")

        print("\nDONE")
        print("=" * 60)

        return {
            "discovered_count": len(discovered),
            "enriched_count": len(enriched),
            "qualified_count": len(qualified),
            "simulated_send_count": simulated_count,
        }

    def _format_tracker_output(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Maps internal dictionary keys to user-facing column headers specified in Section 11."""
        formatted = []
        for r in records:
            item = {
                "Name": r.get("name", ""),
                "Platform": r.get("platform", "YouTube"),
                "Profile URL": r.get("profile_url", ""),
                "Followers": r.get("subscriber_count", 0),
                "Engagement Rate": r.get("engagement_rate", "Not Found"),
                "Niche": r.get("category_niche", "Technology / AI / Developer"),
                "Content Themes": r.get("content_themes", ""),
                "Email": r.get("contact_email", "Not Found"),
                "Recent Content": r.get("recent_video_titles", "Not Found"),
                "Filter Status": r.get("filter_status", ""),
                "Filter Reason": r.get("filter_reason", ""),
                "Email Pitch": r.get("email_pitch", ""),
                "Instagram DM": r.get("instagram_dm", ""),
                "Sending Status": r.get("sending_status", ""),
            }
            formatted.append(item)
        return formatted

    @staticmethod
    def _export_csv(data: List[Dict[str, Any]], filepath: Path):
        """Exports a list of dicts to a CSV file."""
        if not data:
            # Write empty CSV header if data is empty
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                f.write("")
            return

        headers = list(data[0].keys())
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
