from dataclasses import dataclass, field


@dataclass
class Book:
    id: int
    title: str
    authors: list[str]
    genres: list[str]
    description: str
    year: int | None


@dataclass
class BookScore:
    book_id: int
    vector_score: float
    author_score: float
    onboarding_genre_score: float
    genre_score: float
    era_score: float


@dataclass
class User:
    id: int
    username: str | None
    taste_vec: list[float] | None = None
    liked_genres: list[str] = field(default_factory=list)
