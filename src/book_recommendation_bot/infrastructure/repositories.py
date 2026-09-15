from typing import Any

from neo4j import AsyncDriver
from neo4j.exceptions import ConstraintError

from .exceptions import (
    RecordNotFoundError,
    UniqueConstraintViolationError,
)

from book_recommendation_bot.domain.entities import Book, BookScore, User
from book_recommendation_bot.domain.repositories import BookRepository, UserRepository


class Neo4jUserRepository(UserRepository):
    def __init__(self, driver: AsyncDriver):
        self.driver = driver

    async def get_by_id(self, user_id: int) -> User | None:
        query = """
            MATCH (u:User {id: $user_id})

            OPTIONAL MATCH (u)-[:LIKES_GENRE]->(g:Genre)

            RETURN u.id AS id, 
                u.username AS username,
                u.taste_embedding AS taste_vec,
                collect(DISTINCT g.name) AS liked_genres
        """
        async with self.driver.session() as session:
            res = await session.run(query, user_id=user_id)
            r = await res.single()

            if not r:
                return None

            return User(
                id=r["id"],
                username=r["username"],
                taste_vec=r["taste_vec"],
                liked_genres=r["liked_genres"],
            )

    async def get_by_id_lightweight(self, user_id: int) -> User | None:
        query = """
            MATCH (u:User {id: $user_id})

            RETURN u.id AS id, 
                u.username AS username
        """
        async with self.driver.session() as session:
            res = await session.run(query, user_id=user_id)
            r = await res.single()

            if not r:
                return None

            return User(
                id=r["id"],
                username=r["username"],
            )

    async def create(
        self,
        user: User,
    ) -> None:
        query = """
            CREATE (u:User {
                id: $user_id,
                username: $username,
                taste_embedding: $taste_vector,
                created_at: datetime()
            })

            WITH u
            UNWIND $genres AS genre_name
            MERGE (g:Genre {name: genre_name})
            MERGE (u)-[:LIKES_GENRE]->(g)
        """
        async with self.driver.session() as session:
            try:
                await session.run(
                    query,
                    user_id=user.id,
                    username=user.username,
                    taste_vector=user.taste_vec,
                    genres=user.liked_genres,
                )
            except ConstraintError:
                raise UniqueConstraintViolationError(f"User '{user.id}' already exists")

    async def update_profile(self, user: User) -> None:
        query = """
            MATCH (u:User {id: $user_id})

            SET u.username = $username,
                u.last_active_at = datetime()

            RETURN count(u) AS updated_count
        """
        async with self.driver.session() as session:
            res = await session.run(query, user_id=user.id, username=user.username)
            r = await res.single()

            if not r or r["updated_count"] == 0:
                raise RecordNotFoundError(f"User '{user.id}' not exists")

    async def rate_book(self, user_id: int, book_id: int, score: int) -> None:
        query = """
            MATCH (u:User {id: $user_id})
            MATCH (b:Book {id: $book_id})

            MERGE (u)-[r:RATED]->(b)

            ON CREATE SET r.created_at = datetime()
            SET r.score = $score, r.updated_at = datetime()

            RETURN count(r) AS updated_count
        """
        async with self.driver.session() as session:
            res = await session.run(
                query, user_id=user_id, book_id=book_id, score=score
            )
            r = await res.single()

            if not r or r["updated_count"] == 0:
                raise RecordNotFoundError(
                    f"Book '{book_id}' or user '{user_id}' not found"
                )

    async def set_taste_vector(self, user_id: int, taste_vec: list[float]) -> None:
        query = """
            MATCH (u:User {id: $user_id})

            SET u.taste_embedding = $taste_vector,
                u.taste_updated_at = datetime()

            RETURN count(u) AS updated_count
        """
        async with self.driver.session() as session:
            res = await session.run(query, user_id=user_id, taste_vector=taste_vec)
            r = await res.single()

            if not r or r["updated_count"] == 0:
                raise RecordNotFoundError(f"User '{user_id}' not found.")

    async def batch_like_genres(self, user_id: int, genres: list[str]) -> None:
        query = """
            MATCH (u:User {id: $user_id})

            OPTIONAL MATCH (u)-[r:LIKES_GENRE]->()
            DELETE r

            WITH DISTINCT u

            FOREACH (genre_name IN $batch |
                MERGE (g:Genre {name: genre_name})
                MERGE (u)-[:LIKES_GENRE]->(g)
            )

            RETURN count(u) AS user_count
        """
        async with self.driver.session() as session:
            res = await session.run(query, user_id=user_id, batch=genres)
            r = await res.single()

            if not r or r["user_count"] == 0:
                raise RecordNotFoundError(f"User '{user_id}' not found")


class Neo4jBookRepository(BookRepository):
    def __init__(self, driver: AsyncDriver):
        self.driver = driver

    async def get_by_id(self, book_id: int) -> Book | None:
        query = """
            MATCH (b:Book {id: $book_id})

            OPTIONAL MATCH (b)-[:WRITTEN_BY]->(a:Author)
            OPTIONAL MATCH (b)-[:HAS_GENRE]->(g:Genre)

            RETURN b.id AS id,
                b.title AS title,
                b.description AS description,
                b.year AS year,
                collect(DISTINCT a.name) AS authors,
                collect(DISTINCT g.name) AS genres
        """
        async with self.driver.session() as session:
            res = await session.run(query, book_id=book_id)
            r = await res.single()

            if not r:
                return None

            return Book(
                id=r["id"],
                title=r["title"],
                authors=r["authors"],
                genres=r["genres"],
                description=r["description"],
                year=r["year"],
            )

    async def get_embedding_by_id(self, book_id: int) -> list[float]:
        query = """
            MATCH (b:Book {id: $book_id})
            
            RETURN b.embedding AS embedding
        """
        async with self.driver.session() as session:
            res = await session.run(query, book_id=book_id)
            r = await res.single()

            if not r:
                raise RecordNotFoundError(f"Book '{book_id}' not found")

            return r["embedding"]

    async def get_recommendations_by_taste(
        self, user_id: int, taste_vector: list[float], limit: int = 1
    ) -> list[tuple[Book, BookScore]]:
        query = """
            CALL db.index.vector.queryNodes('book_embeddings', 100, $taste_vector)
            YIELD node AS rec, score AS vector_score

            MATCH (u:User {id: $user_id})
            WHERE NOT EXISTS { (u)-[:RATED]->(rec) }

            CALL (rec, u) {
                OPTIONAL MATCH (rec)-[:WRITTEN_BY]->(a:Author)<-[:WRITTEN_BY]-(:Book)<-[r:RATED]-(u)
                RETURN coalesce(avg(r.score - 3), 0.0) * 0.15 AS author_score
            }

            CALL (rec, u) {
                OPTIONAL MATCH (rec)-[:HAS_GENRE]->(g:Genre)<-[:LIKES_GENRE]-(u)
                WITH count(DISTINCT g) * 0.15 AS raw_onboarding_score

                RETURN CASE 
                    WHEN raw_onboarding_score > 0.30 THEN 0.30 
                    ELSE raw_onboarding_score 
                END AS onboarding_genre_score
            }

            CALL (rec, u) {
                OPTIONAL MATCH (rec)-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(:Book)<-[r:RATED]-(u)
                RETURN coalesce(avg(r.score - 3), 0.0) * 0.10 AS genre_score
            }

            CALL (rec, u) {
                OPTIONAL MATCH (u)-[r:RATED]->(fav:Book)
                WHERE r.score >= 4 
                AND rec.year IS NOT NULL 
                AND fav.year IS NOT NULL 
                AND abs(rec.year - fav.year) <= 10
                RETURN CASE 
                    WHEN count(DISTINCT fav) * 0.02 > 0.10 THEN 0.10 
                    ELSE count(DISTINCT fav) * 0.02 
                END AS era_score
            }

            WITH rec, 
                vector_score,
                author_score,
                onboarding_genre_score,
                genre_score,
                era_score,
                (vector_score + author_score + onboarding_genre_score + genre_score + era_score) AS total_score
            ORDER BY total_score DESC
            LIMIT $limit

            OPTIONAL MATCH (rec)-[:WRITTEN_BY]->(a:Author)
            OPTIONAL MATCH (rec)-[:HAS_GENRE]->(g:Genre)
            RETURN rec.id AS id, 
                rec.title AS title, 
                rec.description AS description,
                rec.year AS year,
                collect(DISTINCT a.name) AS authors, 
                collect(DISTINCT g.name) AS genres,
                total_score,
                vector_score,
                author_score,
                onboarding_genre_score,
                genre_score,
                era_score
        """
        async with self.driver.session() as session:
            res = await session.run(
                query,
                user_id=user_id,
                taste_vector=taste_vector,
                limit=limit,
            )
            records = await res.data()
            return self._result_from_records(records)

    async def get_fallback_recommendations(
        self, user_id: int, limit: int = 1
    ) -> list[tuple[Book, BookScore]]:
        query = """
            MATCH (u:User {id: $user_id})

            MATCH (rec:Book)-[:HAS_GENRE]->(candidate_g:Genre)
            WHERE ((u)-[:LIKES_GENRE]->(candidate_g) 
            OR EXISTS { (candidate_g)<-[:HAS_GENRE]-(:Book)<-[r:RATED]-(u) WHERE r.score >= 4 })
            AND NOT EXISTS { (u)-[:RATED]->(rec) }

            CALL (rec, u) {
                OPTIONAL MATCH (rec)-[:WRITTEN_BY]->(a:Author)<-[:WRITTEN_BY]-(:Book)<-[r:RATED]-(u)
                RETURN coalesce(avg(r.score - 3), 0.0) * 0.15 AS author_score
            }

            CALL (rec, u) {
                OPTIONAL MATCH (rec)-[:HAS_GENRE]->(g:Genre)<-[:LIKES_GENRE]-(u)
                WITH count(DISTINCT g) * 0.15 AS raw_onboarding_score

                RETURN CASE 
                    WHEN raw_onboarding_score > 0.30 THEN 0.30 
                    ELSE raw_onboarding_score 
                END AS onboarding_genre_score
            }

            CALL (rec, u) {
                OPTIONAL MATCH (rec)-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(:Book)<-[r:RATED]-(u)
                RETURN coalesce(avg(r.score - 3), 0.0) * 0.10 AS genre_score
            }

            CALL (rec, u) {
                OPTIONAL MATCH (u)-[r:RATED]->(fav:Book)
                WHERE r.score >= 4 
                AND rec.year IS NOT NULL 
                AND fav.year IS NOT NULL 
                AND abs(rec.year - fav.year) <= 10
                RETURN CASE 
                    WHEN count(DISTINCT fav) * 0.02 > 0.10 THEN 0.10 
                    ELSE count(DISTINCT fav) * 0.02 
                END AS era_score
            }

            WITH rec, 
                0.0 AS vector_score,
                author_score,
                onboarding_genre_score,
                genre_score,
                era_score,
                (author_score + onboarding_genre_score + genre_score + era_score) AS total_score
            ORDER BY total_score DESC, rand()
            LIMIT $limit

            OPTIONAL MATCH (rec)-[:WRITTEN_BY]->(a:Author)
            OPTIONAL MATCH (rec)-[:HAS_GENRE]->(g:Genre)
            RETURN rec.id AS id, 
                rec.title AS title, 
                rec.description AS description,
                rec.year AS year,
                collect(DISTINCT a.name) AS authors, 
                collect(DISTINCT g.name) AS genres,
                total_score,
                vector_score,
                author_score,
                onboarding_genre_score,
                genre_score,
                era_score
        """
        async with self.driver.session() as session:
            res = await session.run(query, user_id=user_id, limit=limit)
            records = await res.data()
            return self._result_from_records(records)

    def _result_from_records(
        self, records: list[dict[str, Any]]
    ) -> list[tuple[Book, BookScore]]:
        return [
            (
                Book(
                    id=r["id"],
                    title=r["title"],
                    authors=r["authors"],
                    genres=r["genres"],
                    description=r["description"],
                    year=r["year"],
                ),
                BookScore(
                    book_id=r["id"],
                    vector_score=r["vector_score"],
                    author_score=r["author_score"],
                    onboarding_genre_score=r["onboarding_genre_score"],
                    genre_score=r["genre_score"],
                    era_score=r["era_score"],
                ),
            )
            for r in records
        ]
