from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import (
    delete_confirm_keyboard,
    delete_menu_keyboard,
    history_delete_keyboard,
    transaction_delete_confirm_keyboard,
    undo_delete_keyboard,
)
from app.handlers.common import get_user_from_callback, get_user_from_message
from app.models import DeleteType
from app.repositories.transaction_repository import TransactionRepository
from app.services.delete_service import DeleteService
from app.services.report_service import ReportService
from app.utils.dates import format_date, format_time
from app.utils.money import format_money
from app.utils.text import html

router = Router(name="deletions")


@router.message(Command("delete", "clear"))
async def cmd_delete(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    await message.answer("Что удалить?", reply_markup=delete_menu_keyboard())


@router.message(Command("undo_delete"))
async def cmd_undo_delete(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    batch = await DeleteService(session).undo_last(user.id)
    if batch is None:
        await message.answer("Нет удаления, которое можно восстановить.")
        return
    await message.answer(f"Восстановил {batch.transactions_count} записей.")


@router.callback_query(F.data == "delete:menu")
async def cb_delete_menu(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer("Что удалить?", reply_markup=delete_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "delete:cancel")
async def cb_delete_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.answer("Действие отменено.")
    await callback.answer()


@router.callback_query(F.data == "delete:last")
async def cb_delete_last(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.message is None:
        return
    batch = await DeleteService(session).delete_last(user.id)
    await _answer_deleted(callback.message, batch)
    await callback.answer()


@router.callback_query(F.data == "delete:history")
async def cb_delete_history(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.message is None:
        return
    await _send_history_for_delete(callback.message, session, user, state)
    await callback.answer()


@router.callback_query(F.data.startswith("tx:delete:"))
async def cb_tx_delete_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None or callback.message is None:
        return
    transaction_id = int(callback.data.rsplit(":", 1)[-1])
    transaction = await TransactionRepository(session).get_by_id(transaction_id, user.id)
    if transaction is None or transaction.is_deleted:
        await callback.message.answer("Это действие уже недоступно. Открой историю заново.")
        await callback.answer()
        return
    await callback.message.answer(
        "Удалить эту запись?\n\n" + _transaction_line(transaction, user.settings.timezone),
        reply_markup=transaction_delete_confirm_keyboard(transaction.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tx:confirm_delete:"))
async def cb_tx_delete_apply(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None or callback.message is None:
        return
    transaction_id = int(callback.data.rsplit(":", 1)[-1])
    batch = await DeleteService(session).delete_single(user.id, transaction_id)
    await _answer_deleted(callback.message, batch)
    await callback.answer()


@router.callback_query(F.data.startswith("delete:toggle:"))
async def cb_delete_toggle(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None or callback.message is None:
        return
    transaction_id = int(callback.data.rsplit(":", 1)[-1])
    data = await state.get_data()
    candidate_ids = [int(item) for item in data.get("delete_candidate_ids", [])]
    if transaction_id not in candidate_ids:
        await callback.message.answer("Это действие уже недоступно. Открой историю заново.")
        await callback.answer()
        return
    selected_ids = {int(item) for item in data.get("delete_selected_ids", [])}
    if transaction_id in selected_ids:
        selected_ids.remove(transaction_id)
    else:
        selected_ids.add(transaction_id)
    await state.update_data(delete_selected_ids=sorted(selected_ids))
    history = await ReportService(session).history(user, limit=10)
    await callback.message.answer(
        ReportService(session).render_history(history, user.settings.timezone),
        reply_markup=history_delete_keyboard(candidate_ids, selected_ids=selected_ids),
    )
    await callback.answer()


@router.callback_query(F.data == "delete:selected_confirm")
async def cb_delete_selected_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected_ids = [int(item) for item in data.get("delete_selected_ids", [])]
    if callback.message is None:
        return
    if not selected_ids:
        await callback.message.answer("Сначала выбери записи.")
        await callback.answer()
        return
    await callback.message.answer(
        f"Удалить выбранные записи?\n\nБудет удалено: {len(selected_ids)} записей.",
        reply_markup=delete_confirm_keyboard("custom", len(selected_ids)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete:preview:"))
async def cb_delete_preview(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None or callback.message is None:
        return
    delete_type = _parse_delete_type(callback.data.rsplit(":", 1)[-1])
    if delete_type is None:
        await callback.answer("Действие недоступно.", show_alert=True)
        return
    preview = await DeleteService(session).preview(user, delete_type)
    if preview.count == 0:
        await callback.message.answer("Нет записей для удаления.")
        await callback.answer()
        return
    await callback.message.answer(
        _preview_text(preview.title, preview.count, preview.period, delete_type),
        reply_markup=delete_confirm_keyboard(delete_type.value, preview.count),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete:apply:"))
async def cb_delete_apply(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None or callback.message is None:
        return
    delete_type_value = callback.data.rsplit(":", 1)[-1]
    service = DeleteService(session)
    if delete_type_value == DeleteType.CUSTOM.value:
        data = await state.get_data()
        selected_ids = [int(item) for item in data.get("delete_selected_ids", [])]
        batch = await service.delete_selected(user.id, selected_ids)
        await state.clear()
    else:
        delete_type = _parse_delete_type(delete_type_value)
        batch = await service.delete_by_type(user, delete_type) if delete_type else None
    await _answer_deleted(callback.message, batch)
    await callback.answer()


@router.callback_query(F.data.startswith("undo_delete:"))
async def cb_undo_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None or callback.message is None:
        return
    batch_id = int(callback.data.rsplit(":", 1)[-1])
    batch = await DeleteService(session).undo_last(user.id, batch_id)
    if batch is None:
        await callback.message.answer("Восстановление уже недоступно.")
    else:
        await callback.message.answer(f"Восстановил {batch.transactions_count} записей.")
    await callback.answer()


async def _send_history_for_delete(message, session: AsyncSession, user, state: FSMContext) -> None:
    history = await ReportService(session).history(user, limit=10)
    transaction_ids = [item.id for item in history]
    await state.update_data(delete_candidate_ids=transaction_ids, delete_selected_ids=[])
    await message.answer(
        ReportService(session).render_history(history, user.settings.timezone),
        reply_markup=history_delete_keyboard(transaction_ids),
    )


async def _answer_deleted(message, batch) -> None:
    if batch is None:
        await message.answer("Нет записей для удаления.")
        return
    await message.answer(
        f"Записи удалены: {batch.transactions_count}.",
        reply_markup=undo_delete_keyboard(batch.id),
    )


def _parse_delete_type(value: str) -> DeleteType | None:
    try:
        return DeleteType(value)
    except ValueError:
        return None


def _preview_text(title: str, count: int, period: str, delete_type: DeleteType) -> str:
    if delete_type == DeleteType.ALL:
        return (
            "Внимание. Ты собираешься удалить ВСЕ свои записи.\n\n"
            f"Будет удалено: {count} записей.\n"
            "Это действие очистит историю расходов и доходов, отчеты и баланс. "
            "Зарплатные периоды останутся, но операции не будут учитываться."
        )
    return (
        f"Ты собираешься удалить {title}.\n\n"
        f"Будет удалено: {count} записей\n"
        f"Период: {period}\n\n"
        "Это действие изменит отчеты и баланс."
    )


def _transaction_line(transaction, timezone: str) -> str:
    title = transaction.comment or transaction.category_name or "операция"
    return (
        f"{html(title.capitalize())} — {format_money(transaction.amount, transaction.currency)}\n"
        f"Дата: {format_date(transaction.operation_datetime, timezone)}\n"
        f"Время: {format_time(transaction.operation_datetime, timezone)}"
    )
