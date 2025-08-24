import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = "telegram_videos"  # Replace with your actual database name if different

client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
videos_collection = db.videos
fs_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="thumbnails")

async def save_video_document(doc: dict) -> str:
    """Insert video metadata and return inserted ID."""
    result = await videos_collection.insert_one(doc)
    return str(result.inserted_id)
