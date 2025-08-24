import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from dotenv import load_dotenv
from logging_config import setup_logging

load_dotenv()
logger = setup_logging()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = "telegram_videos"

logger.info(f"Initializing MongoDB connection to: {MONGODB_URI}")

try:
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    videos_collection = db.videos
    fs_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="thumbnails")
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

async def save_video_document(doc: dict) -> str:
    """Insert video metadata and return inserted ID."""
    try:
        logger.info(f"Attempting to save video document: file_id={doc.get('file_id')}")
        result = await videos_collection.insert_one(doc)
        inserted_id = str(result.inserted_id)
        logger.info(f"✅ Successfully saved video to database! Document ID: {inserted_id}")
        logger.info(f"Video details - File ID: {doc.get('file_id')}, Caption: {doc.get('caption', 'No caption')}")
        return inserted_id
    except Exception as e:
        logger.error(f"❌ Failed to save video document to database: {e}")
        raise

async def get_videos_count() -> int:
    """Get total count of videos in database."""
    try:
        count = await videos_collection.count_documents({})
        logger.info(f"Total videos in database: {count}")
        return count
    except Exception as e:
        logger.error(f"Failed to get videos count: {e}")
        return 0
