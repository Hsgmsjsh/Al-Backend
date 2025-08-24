import os
import tempfile
import ffmpeg
import logging
from telegram import Bot
from dotenv import load_dotenv
from logging_config import setup_logging

load_dotenv()
logger = setup_logging()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

def download_video(file_id: str) -> str:
    """Download video from Telegram to a temp file; return local path."""
    try:
        logger.info(f"Downloading video with file_id: {file_id}")
        file = bot.get_file(file_id)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        file.download(custom_path=tmp.name)
        logger.info(f"✅ Video downloaded successfully to: {tmp.name}")
        return tmp.name
    except Exception as e:
        logger.error(f"❌ Failed to download video {file_id}: {e}")
        raise

def get_builtin_thumbnail(video_message) -> str | None:
    """Return a thumbnail file_id if Telegram provided one."""
    try:
        if hasattr(video_message, 'thumb') and video_message.thumb:
            logger.info("✅ Built-in thumbnail found from Telegram")
            return video_message.thumb.file_id
        logger.info("ℹ️ No built-in thumbnail available")
        return None
    except Exception as e:
        logger.error(f"Error checking built-in thumbnail: {e}")
        return None

def generate_thumbnail(video_path: str) -> str:
    """Capture 1-second frame from video; return thumbnail path."""
    try:
        logger.info(f"Generating thumbnail for video: {video_path}")
        thumb_fd, thumb_path = tempfile.mkstemp(suffix=".jpg")
        os.close(thumb_fd)
        
        (
            ffmpeg
            .input(video_path, ss=1)
            .output(thumb_path, vframes=1, format='image2', vcodec='mjpeg')
            .run(overwrite_output=True, quiet=True)
        )
        
        logger.info(f"✅ Thumbnail generated successfully: {thumb_path}")
        return thumb_path
    except Exception as e:
        logger.error(f"❌ Failed to generate thumbnail: {e}")
        raise

def cleanup_temp_files(*file_paths):
    """Clean up temporary files."""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")
