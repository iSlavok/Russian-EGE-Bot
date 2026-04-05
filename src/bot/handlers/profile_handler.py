from collections.abc import Sequence

from aiogram import F, Router
from aiogram.types import CallbackQuery
from dishka import FromDishka

from app.schemas import UserWithExercisesDTO
from app.schemas.stats_schemas import CategoryStatItemDTO, ProfileSummaryDTO
from app.services.category_service import CategoryService
from app.services.stats_service import StatsService
from bot.callback_datas import StatsCategoryCallbackData
from bot.keyboards import (
    get_profile_keyboard,
    get_stats_back_keyboard,
    get_stats_categories_keyboard,
)
from bot.services import MessageManager

router = Router(name="profile_router")


def _format_profile(summary: ProfileSummaryDTO) -> str:
    date_str = summary.registered_at.strftime("%d.%m.%Y")
    pct_str = f" ({summary.correct_percent}%)" if summary.total_answered > 0 else ""
    lines = [
        "👤 <b>Профиль</b>",
        "",
        f"Имя: {summary.full_name}",
        f"Зарегистрирован: {date_str}",
        "",
        f"Решено заданий: {summary.total_answered}",
        f"Правильных: {summary.total_correct}{pct_str}",
        f"Серия: {summary.current_streak} | Лучшая: {summary.max_streak}",
        f"Дней подряд: {summary.current_daily_streak}",
    ]
    return "\n".join(lines)


def _format_overview_stats(summary: ProfileSummaryDTO, items: Sequence[CategoryStatItemDTO]) -> str:
    pct_str = f" ({summary.correct_percent}%)" if summary.total_answered > 0 else ""
    lines = [
        "📊 <b>Статистика</b>",
        "",
        f"Всего решено: {summary.total_answered}",
        f"Правильных: {summary.total_correct}{pct_str}",
        "",
        "<b>По заданиям:</b>",
    ]
    lines.extend(_format_stat_line(item) for item in items)
    if not items:
        lines.append("  Нет данных")
    return "\n".join(lines)


def _format_stat_line(item: CategoryStatItemDTO) -> str:
    if item.total_answered == 0:
        return f"  {item.name} — не решалось"
    return f"  {item.name} — решено: {item.total_answered}, верно: {item.total_correct} ({item.percent}%)"


def _format_stats_list(title: str, items: Sequence[CategoryStatItemDTO]) -> str:
    lines = [f"📊 <b>{title}</b>", ""]
    lines.extend(_format_stat_line(item) for item in items)
    if not items:
        lines.append("  Нет данных")
    return "\n".join(lines)


def _format_single_stats(name: str, item: CategoryStatItemDTO) -> str:
    lines = [f"📊 <b>{name}</b>", ""]
    if item.total_answered == 0:
        lines.append("Не решалось")
    else:
        lines.append(f"Решено: {item.total_answered}")
        lines.append(f"Верно: {item.total_correct} ({item.percent}%)")
    return "\n".join(lines)



@router.callback_query(F.data == "profile")
async def show_profile(
    callback_query: CallbackQuery,
    user: UserWithExercisesDTO,
    message_manager: MessageManager,
    stats_service: FromDishka[StatsService],
) -> None:
    summary = await stats_service.get_profile_summary(
        user_id=user.id,
        full_name=user.full_name,
        registered_at=user.created_at,
    )
    await message_manager.edit_message(text=_format_profile(summary), reply_markup=get_profile_keyboard())
    await callback_query.answer()


@router.callback_query(F.data == "profile_stats")
async def show_stats(
    callback_query: CallbackQuery,
    user: UserWithExercisesDTO,
    message_manager: MessageManager,
    stats_service: FromDishka[StatsService],
) -> None:
    summary = await stats_service.get_profile_summary(
        user_id=user.id,
        full_name=user.full_name,
        registered_at=user.created_at,
    )
    items = await stats_service.get_children_stats(user.id, parent_id=None)
    text = _format_overview_stats(summary, items)
    keyboard = get_stats_categories_keyboard(items, back_callback="profile")
    await message_manager.edit_message(text=text, reply_markup=keyboard)
    await callback_query.answer()


@router.callback_query(StatsCategoryCallbackData.filter())
async def show_stats_category(
    callback_query: CallbackQuery,
    user: UserWithExercisesDTO,
    callback_data: StatsCategoryCallbackData,
    message_manager: MessageManager,
    stats_service: FromDishka[StatsService],
    category_service: FromDishka[CategoryService],
) -> None:
    category = await category_service.get_by_id_with_children(callback_data.category_id)

    # Back button target
    if category.parent_id:
        back_cb = StatsCategoryCallbackData(category_id=category.parent_id).pack()
    else:
        back_cb = "profile_stats"

    if category.is_ege_task:
        # EGE task — show its aggregated stats, no further buttons
        item = await stats_service.get_category_aggregated_stats(user.id, category.id)
        text = _format_single_stats(category.name, item)
        keyboard = get_stats_back_keyboard(back_cb)

    elif not category.children:
        # Leaf non-EGE (edge case) — show its own stats
        item = await stats_service.get_category_aggregated_stats(user.id, category.id)
        text = _format_single_stats(category.name, item)
        keyboard = get_stats_back_keyboard(back_cb)

    elif all(c.is_ege_task for c in category.children):
        # All children are EGE — terminal view: text only
        items = await stats_service.get_children_stats(user.id, category.id)
        text = _format_stats_list(category.name, items)
        keyboard = get_stats_back_keyboard(back_cb)

    else:
        # Mix of EGE and non-EGE — show buttons for navigation
        items = await stats_service.get_children_stats(user.id, category.id)
        text = _format_stats_list(category.name, items)
        keyboard = get_stats_categories_keyboard(items, back_callback=back_cb)

    await message_manager.edit_message(text=text, reply_markup=keyboard)
    await callback_query.answer()
