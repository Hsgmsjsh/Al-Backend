import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from bson import ObjectId
from database import videos_collection, fs_bucket
from schemas import VideoOut

app = FastAPI(title="Telegram Video Indexer")

@app.get("/videos", response_model=list[VideoOut])
async def list_videos():
    videos = []
    async for doc in videos_collection.find().sort("date_uploaded", -1):
        grid_id = doc["thumbnail_file_id"]
        thumb_url = f"{os.getenv('API_BASE_URL')}/thumbnail/{grid_id}"
        download_url = (
            f"https://api.telegram.org/file/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/"
            f"{(await fs_bucket.find_one({'_id': ObjectId(grid_id)})).filename}"
        )
        videos.append(VideoOut(
            id=str(doc["_id"]),
            file_id=doc["file_id"],
            thumbnail_url=thumb_url,
            download_url=download_url,
            caption=doc.get("caption"),
            date_uploaded=doc["date_uploaded"].isoformat()
        ))
    return videos

@app.get("/thumbnail/{file_id}")
async def get_thumbnail(file_id: str):
    try:
        grid_out = await fs_bucket.open_download_stream(ObjectId(file_id))
        return StreamingResponse(grid_out, media_type="image/jpeg")
    except Exception:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
