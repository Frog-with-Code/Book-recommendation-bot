from book_recommendation_bot.application.exceptions import (
    BookNotFoundError,
    RecommendationsExhaustedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from book_recommendation_bot.domain.entities import Book, BookScore, User
from book_recommendation_bot.domain.repositories import BookRepository, UserRepository
from book_recommendation_bot.domain.utils import calculate_ema_taste_vector
from book_recommendation_bot.infrastructure.embeddings import EmbeddingService
from book_recommendation_bot.infrastructure.exceptions import (
    RecordNotFoundError,
    UniqueConstraintViolationError,
)


class RecommendationService:
    def __init__(
        self,
        user_repo: UserRepository,
        book_repo: BookRepository,
        embedding_service: EmbeddingService,
    ):
        self.user_repo = user_repo
        self.book_repo = book_repo
        self.embedding_service = embedding_service

    async def register_user(
        self,
        user_id: int,
        username: str | None,
        book_description: str,
        liked_genres: list[str],
    ) -> None:
        taste_vec = self.embedding_service.embed_query(book_description)

        user = User(
            id=user_id,
            username=username,
            taste_vec=taste_vec,
            liked_genres=liked_genres,
        )

        try:
            await self.user_repo.create(user=user)
        except UniqueConstraintViolationError as e:
            raise UserAlreadyExistsError(str(e)) from e

    async def rate_book(self, user_id: int, book_id: int, score: int) -> None:
        try:
            book_embedding = await self.book_repo.get_embedding_by_id(book_id)
        except RecordNotFoundError as e:
            raise BookNotFoundError(str(e)) from e

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User '{user_id}' not found")

        await self.user_repo.rate_book(user_id, book_id, score)

        new_taste = calculate_ema_taste_vector(user.taste_vec, book_embedding, score)
        if new_taste:
            user.taste_vec = new_taste
            await self.user_repo.update_profile(user)

    async def get_next_book(self, user_id: int) -> tuple[Book, BookScore]:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User '{user_id}' not found")

        if user.taste_vec is None:
            books = await self.book_repo.get_fallback_recommendations(
                user_id=user_id, limit=1
            )
        else:
            books = await self.book_repo.get_recommendations_by_taste(
                user_id=user_id, taste_vector=user.taste_vec, limit=1
            ) or await self.book_repo.get_fallback_recommendations(
                user_id=user_id, limit=1
            )

        if not books:
            raise RecommendationsExhaustedError("No recommendations were found!")

        return books[0]

    async def get_book_by_description(
        self, user_id: int, description: str
    ) -> tuple[Book, BookScore]:
        if not await self.is_user_registered(user_id):
            raise UserNotFoundError(f"User '{user_id}' not found")

        desc_vec = self.embedding_service.embed_query(description)

        books = await self.book_repo.get_recommendations_by_taste(
            user_id=user_id, taste_vector=desc_vec
        )

        if not books or books[0][1].vector_score < 0.5:
            raise RecommendationsExhaustedError(
                "No recommendations with such description were found!"
            )

        return books[0]

    async def is_user_registered(self, user_id: int) -> bool:
        user = await self.user_repo.get_by_id_lightweight(user_id)
        return user is not None

    async def select_favorite_genres(self, user_id: int, genres: list[str]) -> None:
        try:
            await self.user_repo.batch_like_genres(user_id, genres)
        except RecordNotFoundError as e:
            raise UserNotFoundError(str(e)) from e
