import asyncio

from neo4j import AsyncGraphDatabase
from aiogram import Bot, Dispatcher

from book_recommendation_bot.application.services import RecommendationService
from book_recommendation_bot.infrastructure.embeddings import EmbeddingService
from book_recommendation_bot.infrastructure.repositories import (
    Neo4jBookRepository,
    Neo4jUserRepository,
)
from book_recommendation_bot.presentation.handlers import router

from .config import EMBEDDING_SERVICE_MODEL, config


async def main():
    driver = AsyncGraphDatabase.driver(
        uri=config.NEO4J_URI,
        auth=(config.NEO4J_USER, config.NEO4J_PASSWORD.get_secret_value()),
    )

    user_repo = Neo4jUserRepository(driver)
    book_repo = Neo4jBookRepository(driver)
    embedding_service = EmbeddingService(EMBEDDING_SERVICE_MODEL)
    service = RecommendationService(user_repo, book_repo, embedding_service)

    bot = Bot(token=config.BOT_TOKEN.get_secret_value())
    dp = Dispatcher()

    dp["service"] = service
    dp.include_router(router)

    try:
        print("Server is running...")
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
