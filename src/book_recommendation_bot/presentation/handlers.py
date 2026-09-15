from contextlib import suppress

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext

from book_recommendation_bot.application.exceptions import (
    BookNotFoundError,
    RecommendationsExhaustedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from book_recommendation_bot.presentation.states import OnboardingState
from book_recommendation_bot.presentation.utils import format_book_card

from .keyboards import get_genres_keyboard, get_rating_keyboard
from .middlewares import EnsureUserMiddleware
from .states import SearchState, GenreSettingsState

from book_recommendation_bot.application.services import RecommendationService

router = Router()
router.message.middleware(EnsureUserMiddleware())
router.callback_query.middleware(EnsureUserMiddleware())


@router.message(CommandStart())
async def start_cmd(
    msg: types.Message,
    user: types.User,
    state: FSMContext,
    service: RecommendationService,
) -> None:
    is_registered = await service.is_user_registered(user.id)

    if is_registered:
        await state.clear()
        await msg.answer(
            "Welcome back! Enter /recommend for receiving book recommendation."
        )
        return

    await state.set_state(OnboardingState.choosing_genres)
    await state.update_data(selected_genres=[])

    await msg.answer(
        "Hi! Let's set up your profile.\n"
        "<b>Step 1/2:</b> Choose up to 3 favorite genres:",
        reply_markup=get_genres_keyboard([]),
        parse_mode="HTML",
    )


@router.callback_query(
    F.data.startswith("toggle_genre:"),
    StateFilter(OnboardingState.choosing_genres, GenreSettingsState.selecting_genres),
)
async def toggle_genre_handler(
    callback: types.CallbackQuery, state: FSMContext
) -> None:
    if not callback.data or not isinstance(callback.message, types.Message):
        return

    genre = callback.data.split(":", 1)[1]

    data = await state.get_data()
    selected_genres: list[str] = data.get("selected_genres", [])

    if genre in selected_genres:
        selected_genres.remove(genre)
        with suppress(TelegramBadRequest):
            await callback.answer()
    else:
        if len(selected_genres) >= 3:
            with suppress(TelegramBadRequest):
                await callback.answer(
                    "⚠️ You can't choose more than 3 genres!", show_alert=True
                )
            return

        selected_genres.append(genre)
        with suppress(TelegramBadRequest):
            await callback.answer()

    await state.update_data(selected_genres=selected_genres)

    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(
            reply_markup=get_genres_keyboard(selected_genres)
        )


@router.callback_query(F.data == "finish_genres", OnboardingState.choosing_genres)
async def finish_genres_step(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback.message, types.Message):
        return

    await callback.answer()

    await state.set_state(OnboardingState.waiting_for_prompt)

    await callback.message.edit_text(
        "Great! Genres are saved!\n\n"
        "<b>Step 2/2:</b> Now write with your own words, what kind of book you want right now\n"
        "<i>(example: science fiction with jack black and cookers)</i>",
        parse_mode="HTML",
    )


@router.message(OnboardingState.waiting_for_prompt)
async def process_prompt_and_register(
    msg: types.Message,
    user: types.User,
    state: FSMContext,
    service: RecommendationService,
) -> None:
    if not msg.text:
        return

    data = await state.get_data()
    selected_genres = data.get("selected_genres", [])

    await msg.answer("⚙️ Creating your profile...")

    try:
        await service.register_user(
            user_id=user.id,
            username=user.username,
            book_description=msg.text if msg.text else "",
            liked_genres=selected_genres,
        )
    except UserAlreadyExistsError:
        await msg.answer("Your profile was already created!")
        return
    finally:
        await state.clear()

    await msg.answer(
        f"🎉 Your profile is ready! Enter /recommend for receiving book recommendation.",
    )


@router.message(Command("recommend"))
async def recommend_cmd(
    msg: types.Message, user: types.User, service: RecommendationService
) -> None:
    try:
        book, score = await service.get_next_book(user.id)
    except RecommendationsExhaustedError:
        await msg.answer("You rated all available books!")
        return
    except UserNotFoundError:
        await msg.answer("You need to register firstly!")
        return

    text = format_book_card(book, score)
    await msg.answer(text, parse_mode="HTML", reply_markup=get_rating_keyboard(book.id))


@router.callback_query(F.data.startswith("rate:"))
async def rate_callback(
    callback: types.CallbackQuery, user: types.User, service: RecommendationService
):
    if not callback.data or not callback.message:
        return

    _, book_id, score = callback.data.split(":")

    try:
        await service.rate_book(user.id, int(book_id), int(score))
    except (BookNotFoundError, UserNotFoundError) as e:
        await callback.answer(str(e))
        return

    await callback.answer(f"Rate was accepted!")

    if isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            "Rate is saved! Enter /recommend to get another book."
        )


@router.message(Command("search"))
async def search_cmd(
    msg: types.Message,
    state: FSMContext,
    user: types.User,
    service: RecommendationService,
) -> None:
    if not await service.is_user_registered(user.id):
        await msg.answer("First register with the command /start")
        return

    await state.set_state(SearchState.waiting_for_description)
    await msg.answer(
        "🔍 <b>Search by the plot</b>\n\n"
        "Now write with your own words, what kind of book you want right now\n"
        "<i>(example: science fiction with jack black and cookers)</i>\n\n"
        "Enter /cancel to exit from the search",
        parse_mode="HTML",
    )


@router.message(SearchState.waiting_for_description)
async def process_search_description(
    msg: types.Message,
    state: FSMContext,
    user: types.User,
    service: RecommendationService,
) -> None:
    if not msg.text:
        return

    if msg.text.strip().lower() == "/cancel":
        await state.clear()
        await msg.answer("Search was cancelled.")
        return

    wait_msg = await msg.answer("⏳ Analyzing the plot...")

    try:
        book, score = await service.get_book_by_description(
            user_id=user.id,
            description=msg.text.strip(),
        )
    except UserNotFoundError:
        await wait_msg.edit_text("User not found. Enter /start to register")
        await state.clear()
        return
    except RecommendationsExhaustedError:
        await wait_msg.edit_text(
            "😔 Unfortunately nothing was found with such description."
        )
        await state.clear()
        return

    await state.clear()

    with suppress(TelegramBadRequest):
        await wait_msg.delete()

    text = format_book_card(book, score)
    await msg.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_rating_keyboard(book.id),
    )


@router.message(Command("genres"))
async def genres_cmd(
    msg: types.Message,
    state: FSMContext,
    user: types.User,
    service: RecommendationService,
) -> None:
    if not await service.is_user_registered(user.id):
        await msg.answer("First register with the command /start")
        return

    current_user = await service.user_repo.get_by_id(user.id)
    current_genres = current_user.liked_genres if current_user else []

    await state.set_state(GenreSettingsState.selecting_genres)
    await state.update_data(selected_genres=current_genres)

    await msg.answer(
        "<b>Setting up favorite genres</b>\n\n"
        "Choose up to 3 favorite genres: "
        "They will increase book's priority in the recommendation list:",
        parse_mode="HTML",
        reply_markup=get_genres_keyboard(current_genres),
    )


@router.callback_query(
    F.data == "finish_genres",
    GenreSettingsState.selecting_genres,
)
async def save_genres_settings(
    callback: types.CallbackQuery,
    state: FSMContext,
    user: types.User,
    service: RecommendationService,
) -> None:
    if not isinstance(callback.message, types.Message):
        return

    with suppress(TelegramBadRequest):
        await callback.answer()

    data = await state.get_data()
    selected_genres = data.get("selected_genres", [])

    try:
        await service.select_favorite_genres(user_id=user.id, genres=selected_genres)
    except UserNotFoundError:
        await callback.message.edit_text("User not found. Enter /start to register")
        await state.clear()
        return

    await state.clear()

    genres_str = ", ".join(selected_genres) if selected_genres else "Not chosen"
    await callback.message.edit_text(
        f"✅ <b>Favorite genres were updated!</b>\n\n"
        f"Your choice: <i>{genres_str}</i>\n\n",
        parse_mode="HTML",
    )
