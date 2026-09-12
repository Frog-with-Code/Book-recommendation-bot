"""Script for importing data into Neo4j

Input:
    - File in CSV format (data/books.csv). Required columns (no register specific):
        - id (int)
        - title (str)
        - description (str)
        - authors (str)
        - genres (str)
        - embedding (str)
    - Model for sentence embedding
"""

import pandas as pd
from neo4j import GraphDatabase

from book_recommendation_bot.config import config
from book_recommendation_bot.domain.consts import (
    UNKNOWN_AUTHOR,
    UNKNOWN_GENRE,
    UNKNOWN_TITLE,
)
from book_recommendation_bot.infrastructure.embeddings import EmbeddingService

embedding_service = EmbeddingService("BAAI/bge-base-en-v1.5")

df = pd.read_csv("data/books.csv").dropna(subset=["description"])
descriptions = df["description"].tolist()

embeddings = embedding_service.embed_documents(descriptions, batch_size=32)

books_batch = []

for i, (_, row) in enumerate(df.iterrows()):
    raw_authors = str(row.get("authors", ""))
    authors = [a.strip() for a in raw_authors.split(",") if a.strip()]
    if not authors:
        authors = [UNKNOWN_AUTHOR]

    raw_genres = str(row.get("genres", ""))
    genres = [g.strip() for g in raw_genres.split(",") if g.strip()]
    if not genres:
        genres = [UNKNOWN_GENRE]

    books_batch.append(
        {
            "id": row.get("id"),
            "title": str(row.get("title", UNKNOWN_TITLE)).strip(),
            "description": str(row.get("description", ""))[:500].strip(),
            "authors": authors,
            "genres": genres,
            "embedding": embeddings[i],
        }
    )

query = """
    UNWIND $batch AS item
    MERGE (b:Book {id: item.id})
    SET b.title = item.title,
        b.description = item.description,
        b.embedding = item.embedding,
        b.year = item.year

    FOREACH (author_name IN item.authors |
        MERGE (a:Author {name: author_name})
        MERGE (b)-[:WRITTEN_BY]->(a)
    )

    FOREACH (genre_name IN item.genres |
        MERGE (g:Genre {name: genre_name})
        MERGE (b)-[:HAS_GENRE]->(g)
    )
"""

uri = config.NEO4J_URI
auth = (config.NEO4J_USER, config.NEO4J_PASSWORD.get_secret_value())

with GraphDatabase.driver(uri, auth=auth) as driver:
    with driver.session() as session:
        print("Importing into Neo4j...")
        session.run(query, batch=books_batch)

print("Done! Books are saved to the graph.")
