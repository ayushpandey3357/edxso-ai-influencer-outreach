import pytest
from app.enrichment import EnrichmentService


def test_extract_valid_email():
    text = "For business inquiries, reach out to contact.alex@techreviews.com or follow on Twitter."
    email = EnrichmentService.extract_email(text)
    assert email == "contact.alex@techreviews.com"


def test_extract_missing_email():
    text = "Welcome to my channel! Check out my tutorials every Tuesday and Thursday."
    email = EnrichmentService.extract_email(text)
    assert email == "Not Found"


def test_never_guess_email():
    text = "Hi, I am John Doe! Creator of Python Tutorials."
    email = EnrichmentService.extract_email(text)
    # Must NOT return john@... or contact@... or anything synthesized
    assert email == "Not Found"


def test_extract_multiple_emails_picks_first_valid():
    text = "Sponsors: sponsor@ai-channel.io, Secondary: info@ai-channel.io"
    email = EnrichmentService.extract_email(text)
    assert email == "sponsor@ai-channel.io"
