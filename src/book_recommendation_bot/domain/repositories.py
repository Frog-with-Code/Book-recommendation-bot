from abc import ABC, abstractmethod

from .entities import Book, BookScore, User


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> User | None:
        pass

    @abstractmethod
    async def get_by_id_lightweight(self, user_id: int) -> User | None:
        pass

    @abstractmethod
    async def create(
        self,
        user: User,
    ) -> None:
        pass

    @abstractmethod
    async def update_profile(self, user: User) -> None:
        pass

    @abstractmethod
    async def rate_book(self, user_id: int, book_id: int, score: int) -> None:
        pass

    @abstractmethod
    async def set_taste_vector(self, user_id: int, taste_vec: list[float]) -> None:
        pass

    @abstractmethod
    async def batch_like_genres(self, user_id: int, genres: list[str]) -> None:
        pass


class BookRepository(ABC):
    @abstractmethod
    async def get_by_id(self, book_id: int) -> Book | None:
        pass

    @abstractmethod
    async def get_embedding_by_id(self, book_id: int) -> list[float]:
        pass

    @abstractmethod
    async def get_recommendations_by_taste(
        self, user_id: int, taste_vector: list[float], limit: int = 1
    ) -> list[tuple[Book, BookScore]]:
        pass

    @abstractmethod
    async def get_fallback_recommendations(
        self, user_id: int, limit: int = 1
    ) -> list[tuple[Book, BookScore]]:
        pass
