from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from book_recommendation_bot.common.exceptions import NotFoundError
from book_recommendation_bot.presentation.states import OnboardingState
from book_recommendation_bot.presentation.utils import format_book_card

from .keyboards import get_genres_keyboard, get_rating_keyboard
from .middlewares import EnsureUserMiddleware

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
    if not msg.from_user:
        return

    is_registered = await service.is_user_registered(user.id)

    if is_registered:
        await state.clear()
        await msg.answer(
            "Welcome back! Enter '/recommend' for receiving book recommendation."
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
    F.data.startswith("toggle_genre:"), OnboardingState.choosing_genres
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
        await callback.answer()
    else:
        if len(selected_genres) >= 3:
            await callback.answer(
                "⚠️ You can't choose more than 3 genres!", show_alert=True
            )
            return

        selected_genres.append(genre)
        await callback.answer()

    await state.update_data(selected_genres=selected_genres)

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

    await service.register_user(
        user_id=user.id,
        username=user.username,
        book_description=msg.text if msg.text else "",
        liked_genres=selected_genres,
    )

    await state.clear()

    await msg.answer(
        f"🎉 Your profile is ready! Enter '/recommend' for receiving book recommendation.",
    )


@router.message(Command("recommend"))
async def recommend_cmd(
    msg: types.Message, user: types.User, service: RecommendationService
) -> None:
    if not await service.is_user_registered(user.id):
        await msg.answer("You need to register firstly!")
        return

    try:
        book, score = await service.get_next_book(user.id)
    except NotFoundError as e:
        await msg.answer("You rated all available books!")
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
    await service.rate_book(user.id, int(book_id), int(score))
    await callback.answer(f"Rate was accepted!")

    if isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            "Rate is saved! Enter /recommend to get another book."
        )
