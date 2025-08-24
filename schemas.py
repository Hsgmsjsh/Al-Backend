from pydantic import BaseModel

class VideoOut(BaseModel):
    id: str
    file_id: str
    thumbnail_url: str
    caption: str | None
    date_uploaded: str
    file_size: int
    duration: int | None
    channel_title: str | None

class HealthResponse(BaseModel):
    status: str
    message: str
    videos_count: int
    timestamp: str
