"""Cancel command handler."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from core.errors import AlreadyCancelledError

router = Router()


def register_cancel_handler(router: Router) -> None:
    """Register cancel handler for bot."""
    router.message.register(cancel_command, Command("cancel"))


async def cancel_command(message: Message):
    """Handle cancel command."""
    await message.answer("ℹ️ Cancellations are not yet implemented.\n\n"
                        "Downloads run to completion for the free tier.")