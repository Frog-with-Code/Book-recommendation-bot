from html import escape
from book_recommendation_bot.domain.entities import Book, BookScore


def format_book_card(book: Book, score: BookScore) -> str:
    safe_title = escape(book.title or "Untitled")
    authors = escape(", ".join(book.authors)) if book.authors else "Unknown author"
    genres = escape(", ".join(book.genres)) if book.genres else "Unknown genre"
    year_str = f"{book.year}" if book.year else "Unknown year"

    card_parts = [
        f"📖 <b>{safe_title}</b>",
        f"<b>Year:</b> {year_str}",
        f"<b>Author:</b> {authors}",
        f"<b>Genre:</b> {genres}\n",
    ]

    if book.description:
        desc = book.description.strip()
        if len(desc) > 600:
            desc = desc[:597] + "..."
        card_parts.append(f"{escape(desc)}\n")

    reasons = _build_recommendation_reasons(score)
    if reasons:
        card_parts.append("💡 <b>Why this book is for you:</b>")
        card_parts.extend([f"* {reason}" for reason in reasons])
        card_parts.append("")

    card_parts.append("⭐️ <i>Rate book recommendation:</i>")

    return "\n".join(card_parts)


def _build_recommendation_reasons(score: BookScore) -> list[str]:
    reasons = []

    print(score)
    if score.vector_score > 0:
        match_percent = round(score.vector_score * 100)
        reasons.append(f"Plot and atmosphere suits you {match_percent}%")
    else:
        reasons.append("Experimental plot recommendation")

    if score.author_score > 0:
        reasons.append("Your liked author")

    if score.onboarding_genre_score > 0:
        reasons.append("Matches the genres from the initial settings")

    if score.genre_score > 0:
        reasons.append("Your liked genre")

    if score.era_score > 0:
        reasons.append("Your liked era")

    return reasons