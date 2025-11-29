from dotenv import load_dotenv
import os
from src.utils import get_logger

load_dotenv()

logger = get_logger(__name__)

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Apify configuration
logger.info("Loading Apify environment variables...")

APIFY_USER_ID = os.getenv("APIFY_USER_ID")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID")

# Log environment variable status
if APIFY_USER_ID:
    logger.info("APIFY_USER_ID loaded successfully")
else:
    logger.warning("APIFY_USER_ID not found in environment variables")

if APIFY_API_TOKEN:
    logger.info("APIFY_API_TOKEN loaded successfully")
else:
    logger.error("APIFY_API_TOKEN not found in environment variables")

if APIFY_ACTOR_ID:
    logger.info(f"APIFY_ACTOR_ID loaded successfully: {APIFY_ACTOR_ID}")
else:
    logger.error("APIFY_ACTOR_ID not found in environment variables")