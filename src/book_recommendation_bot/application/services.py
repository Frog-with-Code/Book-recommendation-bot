from book_recommendation_bot.domain.exceptions import NotFoundError
from book_recommendation_bot.domain.entities import Book, BookScore, User
from book_recommendation_bot.domain.repositories import BookRepository, UserRepository
from book_recommendation_bot.domain.utils import calculate_ema_taste_vector
from book_recommendation_bot.infrastructure.embeddings import EmbeddingService


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
        user = User(id=user_id, username=username)

        taste_vec = self.embedding_service.embed_query(book_description)

        await self.user_repo.create(
            user=user, taste_vector=taste_vec, liked_genres=liked_genres
        )

    async def rate_book(self, user_id: int, book_id: int, score: int) -> None:
        await self.user_repo.rate_book(user_id, book_id, score)

        book_embedding = await self.book_repo.get_embedding_by_id(book_id)
        current_taste = await self.user_repo.get_taste_vector(user_id)

        new_taste = calculate_ema_taste_vector(current_taste, book_embedding, score)

        if new_taste:
            await self.user_repo.set_taste_vector(user_id, new_taste)

    async def get_next_book(self, user_id: int) -> tuple[Book, BookScore]:
        taste_vec = await self.user_repo.get_taste_vector(user_id)
        books = await self.book_repo.get_recommendations_by_taste(
            user_id=user_id, taste_vector=taste_vec, limit=1
        ) or await self.book_repo.get_fallback_recommendations(user_id=user_id, limit=1)

        if not books:
            raise NotFoundError("No books was found!")

        return books[0]

    async def is_user_registered(self, user_id: int) -> bool:
        user = await self.user_repo.get_by_id(user_id)
        return user is not None
