"""Download command handler."""
import asyncio
import os
import re
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core import (
    Platform, MediaType,
    DownloadStatus, get_platform_from_url,
)
from core.constants import UPLOAD_EXTENSIONS, AUDIO_EXTENSIONS, PROGRESS_MESSAGES
from core.errors import normalize_error, BaseError
from utils.logger import logger

router = Router()

# Concurrent downloads per user (kept low for the 512MB Render instance)
MAX_ACTIVE_DOWNLOADS = 1


class DownloadStates(StatesGroup):
    """Download states."""
    waiting_for_url = State()


async def _safe_edit(message: Message, text: str) -> None:
    """Edit a status message, ignoring 'message is not modified' errors."""
    try:
        await message.edit_text(text)
    except Exception:
        pass


def register_download_handler(router: Router) -> None:
    """Register download handler for bot."""
    router.message.register(download_command, Command("start", "help"))
    router.message.register(download_command, Command("download"))
    router.message.register(download_command, F.text.regexp(r"https?://"))


async def download_command(message: Message, state: FSMContext):
    """Handle download command / URL paste."""
    from bot.config import get_config
    config = get_config()

    # Check if message contains URL
    text = message.text or message.caption or ""
    url_match = re.search(r"https?://[^\s]+", text)

    if not url_match:
        # Show help if no URL provided
        from handlers.help import generate_help_text
        help_text = generate_help_text(config)
        await message.answer(help_text, parse_mode="HTML")
        return

    url = url_match.group(0).rstrip(").,]\"'")

    # Concurrency guard (per-user, tracked in FSM)
    active_downloads = (await state.get_data()).get("active_downloads", [])
    if len(active_downloads) >= MAX_ACTIVE_DOWNLOADS:
        await message.answer(
            "⚠️ You already have a download in progress. "
            "Please wait for it to complete."
        )
        return

    # Validate platform
    platform, _ = get_platform_from_url(url)
    if platform in (Platform.OTHER,):
        await message.answer(
            "❌ Unsupported platform. Send a YouTube, Instagram, "
            "Twitter/X, Reddit or Facebook link."
        )
        return

    # Send processing message
    status_msg = await message.answer("⏳ Detecting media...")
    job_id = str(abs(hash(f"{url}_{message.message_id}")))

    active_downloads.append(job_id)
    await state.update_data(
        url=url,
        job_id=job_id,
        message_id=status_msg.message_id,
        active_downloads=active_downloads,
    )

    # Per-job temp dir (cleaned up in `finally`)
    from storage.cleanup import TEMP_MANAGER
    job_dir = TEMP_MANAGER.create_job_dir()

    try:
        # Extract & download (blocking yt-dlp runs in a worker thread)
        from services.extractor import create_extractor
        extractor = create_extractor(config)

        await _safe_edit(
            status_msg,
            f"{PROGRESS_MESSAGES['download']}\n🔗 {platform.value.upper()}",
        )

        filepaths = await extractor.download_media(url, job_dir)

        # Size guard (Telegram Bot API limit is 50MB without a local server)
        max_bytes = config.max_file_size_mb * 1024 * 1024
        for p in filepaths:
            if os.path.getsize(p) > max_bytes:
                from core.errors import FileSizeExceededError
                raise FileSizeExceededError(os.path.getsize(p), max_bytes)

        await _safe_edit(status_msg, PROGRESS_MESSAGES["upload"])

        # Upload
        caption = _build_caption(message.from_user.username if message.from_user else None)
        await _upload_files(message, filepaths, caption, config)

        await _safe_edit(status_msg, PROGRESS_MESSAGES["success"])

    except BaseError as e:
        error_msg = normalize_error(e)
        logger.error(f"Download failed: {error_msg}")
        await _safe_edit(status_msg, f"❌ {error_msg}")
    except Exception as e:
        error_msg = normalize_error(e)
        logger.error(f"Download failed: {error_msg}")
        await _safe_edit(status_msg, f"❌ Download failed: {error_msg}")
    finally:
        # Always clean the job dir (ephemeral Render storage)
        TEMP_MANAGER.force_delete(job_dir)

        # Drop the job from the active list
        data = await state.get_data()
        remaining = [j for j in data.get("active_downloads", []) if j != job_id]
        await state.update_data(active_downloads=remaining)


def _build_caption(username: Optional[str]) -> str:
    """Build a short caption for the uploaded media."""
    who = f"@{username}" if username else "requested"
    return f"📥 Downloaded for {who}"


async def _upload_files(
    message: Message,
    filepaths: list,
    caption: str,
    config,
) -> None:
    """Upload downloaded files to Telegram with type-appropriate methods."""
    from services.uploader import TelegramUploader, truncate_caption

    bot = message.bot
    chat_id = message.chat.id
    uploader = TelegramUploader(bot, config)
    caption, _ = truncate_caption(caption, config.caption_max_length)

    if len(filepaths) > 1:
        # Gallery / multiple files -> media group
        await uploader.upload_media_group(
            chat_id, filepaths, caption=caption, reply_to=message.message_id
        )
        return

    path = filepaths[0]
    ext = os.path.splitext(path)[1].lower()
    size = os.path.getsize(path)

    # >20MB: use FSInputFile so Telegram uploads from disk instead of
    # loading the whole file into RAM (512MB Render instance).
    if size > 20 * 1024 * 1024:
        from aiogram.types import FSInputFile
        if ext in AUDIO_EXTENSIONS:
            await bot.send_audio(
                chat_id, audio=FSInputFile(path),
                caption=caption, title=os.path.basename(path),
                reply_to_message_id=message.message_id,
            )
        elif ext in UPLOAD_EXTENSIONS:
            await bot.send_video(
                chat_id, video=FSInputFile(path),
                caption=caption, reply_to_message_id=message.message_id,
            )
        else:
            await bot.send_document(
                chat_id, document=FSInputFile(path),
                caption=caption, reply_to_message_id=message.message_id,
            )
        return

    if ext in AUDIO_EXTENSIONS:
        await uploader.upload_audio(chat_id, path, caption=caption, reply_to=message.message_id)
    elif ext in {".jpg", ".jpeg", ".png", ".webp"}:
        await uploader.upload_photo(chat_id, path, caption=caption, reply_to=message.message_id)
    elif ext in UPLOAD_EXTENSIONS:
        await uploader.upload_video(chat_id, path, caption=caption, reply_to=message.message_id)
    else:
        await uploader.upload_document(chat_id, path, caption=caption, reply_to=message.message_id)