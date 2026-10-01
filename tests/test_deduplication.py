import pytest
from pathlib import Path
from app.db import DatabaseManager
from app.outreach import OutreachService


def test_db_duplicate_detection(tmp_path: Path):
    db_file = tmp_path / "test_outreach.db"
    db_manager = DatabaseManager(db_path=db_file)

    name = "Jane Tech"
    email = "jane@techblog.io"
    message = "Hello Jane..."

    # First insertion should succeed
    success1 = db_manager.log_outreach(name, email, message, sent=True, status="SIMULATED")
    assert success1 is True

    # Duplicate check method should return True
    assert db_manager.is_duplicate(name, email) is True

    # Second insertion of same (name, email) should fail due to UNIQUE constraint
    success2 = db_manager.log_outreach(name, email, message, sent=True, status="SIMULATED")
    assert success2 is False


def test_outreach_service_skips_duplicates(tmp_path: Path):
    db_file = tmp_path / "test_outreach_service.db"
    db_manager = DatabaseManager(db_path=db_file)
    outreach_service = OutreachService(db_manager=db_manager)

    creator = {
        "name": "Alex Code",
        "contact_email": "alex@codecraft.org",
        "email_pitch": "Sample pitch...",
        "instagram_dm": "Sample DM...",
    }

    # Run 1: Should simulate sending
    res1 = outreach_service.process_outreach([creator])
    assert res1[0]["sending_status"] == "SIMULATED"

    # Run 2: Should mark as SKIPPED_DUPLICATE
    res2 = outreach_service.process_outreach([creator])
    assert res2[0]["sending_status"] == "SKIPPED_DUPLICATE"
