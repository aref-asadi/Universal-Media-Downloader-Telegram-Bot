"""Telegram media uploader."""
import os
from typing import Optional, List, Tuple

from aiogram import Bot
from aiogram.types import BufferedInputFile, InputMediaPhoto, InputMediaVideo

from core.errors import UploaderError
from utils.logger import logger
from utils.mb_convert import format_file_size


class TelegramUploader:
    def __init__(self, bot: Bot, config):
        self.bot = bot
        self.config = config
        self.max_size = config.max_file_size_mb * 1024 * 1024

    async def upload_video(self, chat_id: int, video_path: str, caption: str = "", 
                           thumb_path: Optional[str] = None, reply_to=None) -> dict:
        size = os.path.getsize(video_path)
        if size > self.max_size:
            raise UploaderError(f"Video too large: {format_file_size(size)}")
        
        thumb = BufferedInputFile(open(thumb_path, "rb").read(), "thumb.jpg") if thumb_path else None
        video = BufferedInputFile(open(video_path, "rb").read(), os.path.basename(video_path))
        result = await self.bot.send_video(chat_id, video=video, caption=caption, thumbnail=thumb, reply_to_message_id=reply_to)
        return {"file_id": result.video.file_id, "msg_id": result.message_id}

    async def upload_audio(self, chat_id: int, audio_path: str, caption: str = "",
                           thumb_path: Optional[str] = None, title="Audio", performer="Unknown", reply_to=None) -> dict:
        size = os.path.getsize(audio_path)
        if size > self.max_size:
            raise UploaderError(f"Audio too large")
        thumb = BufferedInputFile(open(thumb_path, "rb").read(), "thumb.jpg") if thumb_path else None
        audio = BufferedInputFile(open(audio_path, "rb").read(), os.path.basename(audio_path))
        result = await self.bot.send_audio(chat_id, audio=audio, caption=caption, thumbnail=thumb, title=title, performer=performer, reply_to_message_id=reply_to)
        return {"file_id": result.audio.file_id, "msg_id": result.message_id}

    async def upload_photo(self, chat_id: int, photo_path: str, caption: str = "", reply_to=None) -> dict:
        size = os.path.getsize(photo_path)
        photo = BufferedInputFile(open(photo_path, "rb").read(), os.path.basename(photo_path))
        result = await self.bot.send_photo(chat_id, photo=photo, caption=caption, reply_to_message_id=reply_to)
        return {"file_id": result.photo[-1].file_id, "msg_id": result.message_id}

    async def upload_media_group(self, chat_id: int, paths: List[str], caption: str = "", reply_to=None) -> dict:
        if not paths: raise UploaderError("No media")
        media = []
        for i, p in enumerate(paths):
            if os.path.getsize(p) > self.max_size: raise UploaderError(f"Media {i} too large")
            if p.lower().endswith(('.jpg','.jpeg','.png')):
                media.append(InputMediaPhoto(media=BufferedInputFile(open(p,"rb").read(),os.path.basename(p)), caption=caption if i==0 else ""))
            else:
                media.append(InputMediaVideo(media=BufferedInputFile(open(p,"rb").read(),os.path.basename(p)), caption=caption if i==0 else ""))
        results = await self.bot.send_media_group(chat_id, media=media, reply_to_message_id=reply_to)
        return {"msg_ids": [r.message_id for r in results], "count": len(results)}

    async def upload_document(self, chat_id: int, path: str, caption: str = "", reply_to=None) -> dict:
        doc = BufferedInputFile(open(path,"rb").read(), os.path.basename(path))
        result = await self.bot.send_document(chat_id, doc, caption=caption, reply_to_message_id=reply_to)
        return {"file_id": result.document.file_id, "msg_id": result.message_id}


def truncate_caption(caption: str, max_len: int = 1000) -> Tuple[str, bool]:
    if len(caption) <= max_len: return caption, False
    return caption[:max_len-3] + "...", True


async def create_uploader(bot: Bot, config): return TelegramUploader(bot, config)