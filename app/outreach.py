import logging
from typing import List, Dict, Any, Optional
from app.db import DatabaseManager
from app.config import Config

logger = logging.getLogger(__name__)


class OutreachService:
    """Handles outreach simulation, duplicate prevention, and logging to SQLite database."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or DatabaseManager()

    def process_outreach(
        self, personalized_influencers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Executes simulated sending layer with duplicate checking and DB persistence.
        """
        outreach_results = []
        logger.info(f"Processing outreach simulation for {len(personalized_influencers)} qualified influencers...")

        for record in personalized_influencers:
            name = record.get("name", "Unknown")
            email = record.get("contact_email", "Not Found")
            email_pitch = record.get("email_pitch", "")
            instagram_dm = record.get("instagram_dm", "")

            # Check for missing email
            if not email or email == "Not Found":
                status = "SKIPPED_NO_EMAIL"
                sent = False
                logger.info(f"Outreach skipped for {name}: No public contact email available.")
            # Check for duplicate outreach
            elif self.db_manager.is_duplicate(name, email):
                status = "SKIPPED_DUPLICATE"
                sent = False
                logger.warning(f"Outreach skipped for {name} ({email}): Already contacted previously.")
            else:
                # Simulate Send
                if Config.SIMULATE_SEND:
                    status = "SIMULATED"
                    sent = True
                    logger.info(f"[SIMULATED EMAIL SENT] To: {name} <{email}> | Pitch: {email_pitch[:60]}...")
                else:
                    # Explicitly safety locked to prevent accidental email dispatch
                    status = "SAFETY_LOCK_ENABLED"
                    sent = False
                    logger.info(f"[SAFETY LOCK] Real email sending disabled by policy.")

                # Log to DB
                self.db_manager.log_outreach(
                    influencer_name=name,
                    email=email,
                    message=email_pitch,
                    sent=sent,
                    status=status,
                )

            # Record final status
            outreach_record = dict(record)
            outreach_record["sending_status"] = status
            outreach_record["instagram_status"] = "MANUAL_REVIEW" if instagram_dm else "N/A"
            outreach_results.append(outreach_record)

        logger.info(f"Outreach processing complete. Processed {len(outreach_results)} records.")
        return outreach_results
