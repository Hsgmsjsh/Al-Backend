 import os
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId

from logging_config import setup_logging
from database import videos_collection, fs_bucket, get_videos_count
from schemas import VideoOut, HealthResponse
from bot import main_bot  # Import the async bot starter

logger = setup_logging()

app = FastAPI(
    title="Telegram Video Indexer API",
    description="Backend API for indexing and serving Telegram videos with thumbnails",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Application startup: log status, start Telegram bot."""
    logger.info("🚀 FastAPI application starting up...")
    try:
        count = await get_videos_count()
        logger.info(f"📊 Current videos in database: {count}")
    except Exception as e:
        logger.error(f"Failed to fetch video count on startup: {e}")

    # Start Telegram bot polling in background
    logger.info("🤖 Starting Telegram bot as background task...")
    asyncio.create_task(main_bot())
    logger.info("✅ Telegram bot background task scheduled")
    logger.info("✅ Application startup completed!")

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint."""
    try:
        videos_count = await get_videos_count()
        response = HealthResponse(
            status="healthy",
            message="Telegram Video Indexer API is running",
            videos_count=videos_count,
            timestamp=datetime.utcnow().isoformat()
        )
        logger.info(f"✅ Health check - {videos_count} videos in database")
        return response
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.get("/videos", response_model=list[VideoOut])
async def list_videos(limit: int = 50, skip: int = 0):
    """List indexed videos with pagination."""
    try:
        logger.info(f"📋 Fetching videos - limit: {limit}, skip: {skip}")
        videos = []
        cursor = videos_collection.find().sort("date_uploaded", -1).skip(skip).limit(limit)
        async for doc in cursor:
            thumbnail_grid_id = doc["thumbnail_file_id"]
            thumbnail_url = f"{os.getenv('API_BASE_URL')}/thumbnail/{thumbnail_grid_id}"
            videos.append(VideoOut(
                id=str(doc["_id"]),
                file_id=doc["file_id"],
                thumbnail_url=thumbnail_url,
                caption=doc.get("caption"),
                date_uploaded=doc["date_uploaded"].isoformat(),
                file_size=doc.get("file_size", 0),
                duration=doc.get("duration"),
                channel_title=doc.get("channel_title")
            ))
        logger.info(f"✅ Fetched {len(videos)} videos")
        return videos
    except Exception as e:
        logger.error(f"❌ Failed to fetch videos: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch videos")

@app.get("/thumbnail/{file_id}")
async def get_thumbnail(file_id: str):
    """Serve thumbnail image from GridFS."""
    try:
        logger.debug(f"🖼️ Serving thumbnail: {file_id}")
        grid_out = await fs_bucket.open_download_stream(ObjectId(file_id))
        async def generate():
            async for chunk in grid_out:
                yield chunk
        return StreamingResponse(generate(), media_type="image/jpeg",
                                 headers={"Cache-Control": "public, max-age=31536000"})
    except Exception as e:
        logger.warning(f"⚠️ Thumbnail not found ({file_id}): {e}")
        raise HTTPException(status_code=404, detail="Thumbnail not found")

@app.get("/video/{file_id}", response_model=VideoOut)
async def get_video_info(file_id: str):
    """Get detailed information about a specific video."""
    try:
        logger.info(f"🎥 Fetching video info: {file_id}")
        doc = await videos_collection.find_one({"file_id": file_id})
        if not doc:
            logger.warning(f"Video not found: {file_id}")
            raise HTTPException(status_code=404, detail="Video not found")
        thumbnail_grid_id = doc["thumbnail_file_id"]
        thumbnail_url = f"{os.getenv('API_BASE_URL')}/thumbnail/{thumbnail_grid_id}"
        video_info = VideoOut(
            id=str(doc["_id"]),
            file_id=doc["file_id"],
            thumbnail_url=thumbnail_url,
            caption=doc.get("caption"),
            date_uploaded=doc["date_uploaded"].isoformat(),
            file_size=doc.get("file_size", 0),
            duration=doc.get("duration"),
            channel_title=doc.get("channel_title")
        )
        logger.info(f"✅ Video info retrieved: {file_id}")
        return video_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch video info: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch video info")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
               
