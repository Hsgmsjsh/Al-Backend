import os
import tempfile
import ffmpeg
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

def download_video(file_id: str) -> str:
    """Download video from Telegram to a temp file; return local path."""
    file = bot.get_file(file_id)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    file.download(custom_path=tmp.name)
    return tmp.name

def get_builtin_thumbnail(file_id: str) -> str | None:
    """Return a thumbnail file_id if Telegram provided one."""
    # This should be passed from message.photo if available
    return None

def generate_thumbnail(video_path: str) -> str:
    """Capture 1-second frame from video; return thumbnail path."""
    thumb_fd, thumb_path = tempfile.mkstemp(suffix=".jpg")
    os.close(thumb_fd)
    (
        ffmpeg
        .input(video_path, ss=1)
        .output(thumb_path, vframes=1)
        .run(overwrite_output=True, quiet=True)
    )
    return thumb_path
