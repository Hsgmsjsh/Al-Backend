from pydantic import BaseModel, Field
from datetime import datetime

class VideoDocument(BaseModel):
    file_id: str = Field(..., description="Telegram file_id")
    file_unique_id: str = Field(..., description="Telegram file_unique_id")
    thumbnail_file_id: str = Field(..., description="GridFS ObjectID for thumbnail")
    mime_type: str = Field(..., description="Video MIME type")
    file_size: int = Field(..., description="Size in bytes")
    caption: str | None = Field(None, description="Optional caption")
    date_uploaded: datetime = Field(..., description="Telegram message date")
