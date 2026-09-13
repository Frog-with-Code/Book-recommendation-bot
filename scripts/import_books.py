import ast
import pandas as pd
from neo4j import GraphDatabase

from book_recommendation_bot.config import EMBEDDING_SERVICE_MODEL, config
from book_recommendation_bot.domain.consts import (
    UNKNOWN_AUTHOR,
    UNKNOWN_GENRE,
    UNKNOWN_TITLE,
)
from book_recommendation_bot.infrastructure.embeddings import EmbeddingService


def parse_list_field(val, default_val: str) -> list[str]:
    if pd.isna(val):
        return [default_val]

    raw = str(val).strip()
    if not raw or raw == "nan":
        return [default_val]

    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, list):
                clean = [
                    str(x).strip(" '\"[]") for x in parsed if str(x).strip(" '\"[]")
                ]
                return clean if clean else [default_val]
        except (ValueError, SyntaxError):
            pass

    raw_cleaned = raw.strip("[]")
    items = [x.strip(" '\"") for x in raw_cleaned.split(",") if x.strip(" '\"")]
    return items if items else [default_val]


embedding_service = EmbeddingService(EMBEDDING_SERVICE_MODEL)

df = pd.read_csv("data/books.csv").dropna(subset=["description"])
descriptions = df["description"].tolist()

embeddings = embedding_service.embed_documents(descriptions, batch_size=32)

books_batch = []

for i, (_, row) in enumerate(df.iterrows()):
    authors = parse_list_field(row.get("authors"), UNKNOWN_AUTHOR)
    genres = parse_list_field(row.get("genres"), UNKNOWN_GENRE)

    year_val = row.get("year")
    year = int(year_val) if pd.notna(year_val) else None

    books_batch.append(
        {
            "id": row.get("id"),
            "title": str(row.get("title", UNKNOWN_TITLE)).strip(),
            "description": str(row.get("description", ""))[:500].strip(),
            "authors": authors,
            "genres": genres,
            "year": year,
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

chunk_size = 500
with GraphDatabase.driver(uri, auth=auth) as driver:
    with driver.session() as session:
        print("Importing into Neo4j...")
        for start_idx in range(0, len(books_batch), chunk_size):
            chunk = books_batch[start_idx : start_idx + chunk_size]
            session.run(query, batch=chunk)
            print(f"Imported {start_idx + len(chunk)} from {len(books_batch)}...")

print("Ready! Books were successfully imported into Neo4j.")
