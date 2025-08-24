import os
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from database import save_video_document, fs_bucket
from utils import download_video, get_builtin_thumbnail, generate_thumbnail
from bson import ObjectId

CHANNEL_ID = os.getenv("CHANNEL_ID")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message.chat and (message.chat.username == CHANNEL_ID.lstrip("@")):
        video = message.video
        file_id = video.file_id
        file_unique_id = video.file_unique_id
        mime_type = video.mime_type or "video/mp4"
        file_size = video.file_size or 0
        date_uploaded = datetime.fromtimestamp(message.date.timestamp())

        # Try Telegram thumbnail
        thumb_file_id = None
        if video.thumb:
            thumb_file_id = video.thumb.file_id

        # If none, generate
        if not thumb_file_id:
            video_path = download_video(file_id)
            thumb_path = generate_thumbnail(video_path)
            # Upload to GridFS
            with open(thumb_path, "rb") as f:
                grid_id = await fs_bucket.upload_from_stream(
                    filename=f"{file_unique_id}.jpg",
                    source=f,
                    metadata={"source": "generated"}
                )
            thumb_file_id = str(grid_id)

        # Save document
        doc = {
            "file_id": file_id,
            "file_unique_id": file_unique_id,
            "thumbnail_file_id": thumb_file_id,
            "mime_type": mime_type,
            "file_size": file_size,
            "caption": message.caption,
            "date_uploaded": date_uploaded
        }
        await save_video_document(doc)

async def main_bot():
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main_bot())
