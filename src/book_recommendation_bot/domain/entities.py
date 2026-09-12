from dataclasses import dataclass


@dataclass
class Book:
    id: str
    title: str
    authors: list[str]
    genres: list[str]
    description: str
    year: int | None


@dataclass
class BookScore:
    book_id: str
    vector_score: float
    author_score: float
    onboarding_genre_score: float
    genre_score: float
    era_score: float


@dataclass
class User:
    id: int
    username: str | None
