import os
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from database import save_video_document, fs_bucket, get_videos_count
from utils import download_video, get_builtin_thumbnail, generate_thumbnail, cleanup_temp_files
from bson import ObjectId
from logging_config import setup_logging

logger = setup_logging()

CHANNEL_ID = os.getenv("CHANNEL_ID")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming video messages from the channel."""
    try:
        message = update.effective_message
        chat = message.chat
        
        logger.info(f"Received message from chat: {chat.title} (@{chat.username})")
        
        # Check if message is from our target channel
        if not (chat.username == CHANNEL_ID.lstrip("@") or chat.title == CHANNEL_ID.lstrip("@")):
            logger.debug(f"Ignoring message from different chat: {chat.username}")
            return
        
        video = message.video
        if not video:
            logger.warning("No video found in message")
            return
        
        logger.info(f"🎥 Processing new video: file_id={video.file_id}")
        logger.info(f"Video details - Duration: {video.duration}s, Size: {video.file_size} bytes")
        
        # Extract video metadata
        file_id = video.file_id
        file_unique_id = video.file_unique_id
        mime_type = video.mime_type or "video/mp4"
        file_size = video.file_size or 0
        duration = video.duration
        date_uploaded = datetime.fromtimestamp(message.date.timestamp())
        caption = message.caption
        channel_title = chat.title
        
        # Handle thumbnail
        thumb_file_id = get_builtin_thumbnail(video)
        video_path = None
        thumb_path = None
        
        try:
            if thumb_file_id:
                # Use Telegram's built-in thumbnail
                logger.info("📸 Using Telegram's built-in thumbnail")
                # Download the thumbnail and store in GridFS
                thumb_file = context.bot.get_file(thumb_file_id)
                thumb_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                thumb_file.download(custom_path=thumb_path)
            else:
                # Generate thumbnail from video
                logger.info("🎬 Generating custom thumbnail from video")
                video_path = download_video(file_id)
                thumb_path = generate_thumbnail(video_path)
            
            # Upload thumbnail to GridFS
            logger.info("💾 Uploading thumbnail to GridFS")
            with open(thumb_path, "rb") as f:
                grid_id = await fs_bucket.upload_from_stream(
                    filename=f"{file_unique_id}.jpg",
                    source=f,
                    metadata={
                        "source": "telegram_built_in" if thumb_file_id else "generated",
                        "video_file_id": file_id,
                        "created_at": datetime.utcnow()
                    }
                )
            
            thumbnail_grid_id = str(grid_id)
            logger.info(f"✅ Thumbnail uploaded to GridFS with ID: {thumbnail_grid_id}")
            
            # Prepare document for database
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
            
            # Save to database
            document_id = await save_video_document(doc)
            
            # Get updated count
            total_videos = await get_videos_count()
            
            logger.info("=" * 60)
            logger.info("🎉 VIDEO SUCCESSFULLY PROCESSED AND SAVED! 🎉")
            logger.info(f"📄 Document ID: {document_id}")
            logger.info(f"🎥 File ID: {file_id}")
            logger.info(f"📸 Thumbnail ID: {thumbnail_grid_id}")
            logger.info(f"📊 Total videos in database: {total_videos}")
            logger.info(f"📝 Caption: {caption or 'No caption'}")
            logger.info("=" * 60)
            
        finally:
            # Cleanup temporary files
            if video_path or thumb_path:
                cleanup_temp_files(video_path, thumb_path)
                
    except Exception as e:
        logger.error(f"❌ Error processing video message: {e}")
        logger.exception("Full error traceback:")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"❌ Bot error occurred: {context.error}")
    if update:
        logger.error(f"Update that caused error: {update}")

async def main_bot():
    """Start the Telegram bot."""
    try:
        logger.info("🤖 Starting Telegram bot...")
        logger.info(f"🎯 Target channel: {CHANNEL_ID}")
        
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(MessageHandler(filters.VIDEO, handle_video))
        app.add_error_handler(error_handler)
        
        # Start bot
        await app.start()
        logger.info("✅ Bot started successfully!")
        logger.info("🔄 Starting polling for updates...")
        
        await app.updater.start_polling(drop_pending_updates=True)
        
        # Keep running
        logger.info("🚀 Bot is now running and listening for videos...")
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        logger.exception("Full error traceback:")
        raise

if __name__ == "__main__":
    asyncio.run(main_bot())
