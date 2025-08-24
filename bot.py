import os
import asyncio
import tempfile
import logging
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from database import save_video_document, fs_bucket, get_videos_count
from utils import download_video, get_builtin_thumbnail, generate_thumbnail, cleanup_temp_files
from logging_config import setup_logging

logger = setup_logging()

CHANNEL_ID = os.getenv("CHANNEL_ID")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming video messages from the channel."""
    try:
        message = update.effective_message
        chat = message.chat

        logger.info(f"Received message in chat: {chat.title} (@{chat.username})")
        if chat.username != CHANNEL_ID.lstrip("@"):
            logger.debug("Ignoring message from non-target channel")
            return

        video = message.video
        if not video:
            logger.warning("No video object found in message")
            return

        # Extract metadata
        file_id = video.file_id
        file_unique_id = video.file_unique_id
        mime_type = video.mime_type or "video/mp4"
        file_size = video.file_size or 0
        duration = video.duration
        date_uploaded = datetime.fromtimestamp(message.date.timestamp())
        caption = message.caption
        channel_title = chat.title

        logger.info(f"Processing video: file_id={file_id}, duration={duration}s, size={file_size} bytes")

        # Thumbnail handling
        thumb_file_id = get_builtin_thumbnail(video)
        video_path = None
        thumb_path = None

        if thumb_file_id:
            logger.info("Using built-in Telegram thumbnail")
            thumb_file = context.bot.get_file(thumb_file_id)
            thumb_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
            thumb_file.download(custom_path=thumb_path)
        else:
            logger.info("Generating custom thumbnail")
            video_path = download_video(file_id)
            thumb_path = generate_thumbnail(video_path)

        # Upload thumbnail to GridFS
        logger.info("Uploading thumbnail to GridFS")
        with open(thumb_path, "rb") as f:
            grid_id = await fs_bucket.upload_from_stream(
                filename=f"{file_unique_id}.jpg",
                source=f,
                metadata={
                    "source": "built_in" if thumb_file_id else "generated",
                    "video_file_id": file_id,
                    "created_at": datetime.utcnow()
                }
            )
        thumbnail_grid_id = str(grid_id)
        logger.info(f"Thumbnail stored in GridFS with ID: {thumbnail_grid_id}")

        # Prepare document
        doc = {
            "file_id": file_id,
            "file_unique_id": file_unique_id,
            "thumbnail_file_id": thumbnail_grid_id,
            "mime_type": mime_type,
            "file_size": file_size,
            "caption": caption,
            "date_uploaded": date_uploaded,
            "channel_title": channel_title,
            "duration": duration
        }

        # Save document to MongoDB
        document_id = await save_video_document(doc)

        # Notify in logs and optionally via bot message
        total_videos = await get_videos_count()
        logger.info("="*60)
        logger.info(f"✅ Video saved! ID: {document_id}")
        logger.info(f"Total videos in DB: {total_videos}")
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"📥 Video indexed: {file_id}\nTotal videos: {total_videos}"
        )
        logger.info("Notification message sent to channel")

    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)

    finally:
        # Cleanup temp files
        cleanup_temp_files(video_path, thumb_path)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Bot error: {context.error}", exc_info=True)

async def main_bot():
    """Start Telegram bot polling."""
    logger.info("Starting Telegram bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_error_handler(error_handler)
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot is polling updates")
    await asyncio.Event().wait()  # Keep running indefinitely

if __name__ == "__main__":
    asyncio.run(main_bot())
                    
