import sys
import logging
from app.config import Config
from app.pipeline import Pipeline
from app.youtube_client import MissingAPIKeyError, QuotaExceededError, YouTubeAPIError


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    setup_logging()
    logger = logging.getLogger("run")

    try:
        pipeline = Pipeline()
        pipeline.run(target_discovery_count=Config.TARGET_DISCOVERY_COUNT)
    except MissingAPIKeyError as e:
        logger.error(f"\n[CONFIGURATION ERROR] {e}")
        logger.error("Please configure your YOUTUBE_API_KEY in the .env file before running discovery.")
        sys.exit(1)
    except QuotaExceededError as e:
        logger.error(f"\n[API QUOTA EXCEEDED] {e}")
        logger.error("YouTube Data API quota limit reached. Try again later or increase quota in GCP Console.")
        sys.exit(1)
    except YouTubeAPIError as e:
        logger.error(f"\n[YOUTUBE API ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n[UNEXPECTED PIPELINE ERROR] {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
