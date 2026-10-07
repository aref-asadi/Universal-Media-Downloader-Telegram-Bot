"""Help command handler."""
from aiogram.types import Message


def generate_help_text(config) -> str:
    """Generate help text for the bot."""
    help_text = """
<b>Universal Media Downloader Bot</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Supported Platforms:</b>
🔥 YouTube - Videos, Shorts, Playlists
📷 Instagram - Posts, Reels, Stories
🐦 Twitter/X - Videos, GIFs, Carousels
🤖 Reddit - Native videos, galleries
📘 Facebook - Video posts

<b>Commands:</b>
/start   - Start the bot and show help
/help    - Show this help message
/download [URL] - Download media from URL
/cancel [ID] - Cancel a download (not yet implemented)

<b>Pricing:</b>
Free 512MB Render Tier - 1 concurrent download

<b>Example:</b>
Send any supported video/image URL directly to the bot

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
© 2024 Universal Media Downloader Bot
    """
    return help_text.strip()


async def help_command(message: Message):
    """Handle help command."""
    from bot.config import get_config
    config = get_config()
    help_text = generate_help_text(config)
    await message.answer(help_text, parse_mode="HTML")