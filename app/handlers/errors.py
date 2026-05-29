import logging

from aiogram import Router
from aiogram.types import ErrorEvent

router = Router(name="errors")
logger = logging.getLogger(__name__)


@router.errors()
async def errors_handler(event: ErrorEvent) -> bool:
    logger.exception("Unhandled update error", exc_info=event.exception)
    try:
        if event.update.message:
            await event.update.message.answer(
                "Произошла ошибка. Я уже записал ее в лог, попробуйте еще раз."
            )
        elif event.update.callback_query and event.update.callback_query.message:
            await event.update.callback_query.message.answer(
                "Произошла ошибка. Я уже записал ее в лог, попробуйте еще раз."
            )
            await event.update.callback_query.answer()
    except Exception:
        logger.exception("Failed to notify user about error")
    return True
