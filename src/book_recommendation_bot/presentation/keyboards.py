from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_rating_keyboard(book_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for score in range(1, 6):
        builder.button(text=f"⭐️ {score}", callback_data=f"rate:{book_id}:{score}")

    builder.adjust(5)

    return builder.as_markup()


POPULAR_GENRES = [
    "Fiction",
    "Fantasy",
    "Science Fiction",
    "Mystery",
    "Thriller",
    "Romance",
    "Biography",
    "History",
    "Poetry",
    "Psychology"
]


def get_genres_keyboard(selected_genres: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for genre in POPULAR_GENRES:
        is_selected = genre in selected_genres
        prefix = "✅ " if is_selected else ""
        builder.button(
            text=f"{prefix}{genre}", 
            callback_data=f"toggle_genre:{genre}"
        )

    builder.adjust(2)

    count = len(selected_genres)
    btn_text = f"➡️ Finish ({count}/3)"
    callback_data = "finish_genres"

    builder.row(InlineKeyboardButton(text=btn_text, callback_data=callback_data))

    return builder.as_markup()
