from pydantic import BaseModel

class VideoOut(BaseModel):
    id: str
    file_id: str
    thumbnail_url: str
    download_url: str
    caption: str | None
    date_uploaded: str
