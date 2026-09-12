"""Script for data cleaning and standardizing

Input:
    - File in CSV format 'data/raw_books.csv'. Required columns (no register specific):
        - title (str)
        - authors (str): last_name, first_name, last_name, first_name and last_name, first_name
        - description (str)
        - category (str)
        - publish date (str)

Output: cleared dataset 'data/books.csv'
"""

import re
import pandas as pd

from book_recommendation_bot.domain.consts import UNKNOWN_AUTHOR, UNKNOWN_GENRE

df = pd.read_csv("data/raw_books.csv")
df.columns = df.columns.str.lower()

df = df.dropna(subset=["description", "title"])
df = df[~df["description"].str.contains("For Ingest Only", na=False)]
df = df[df["description"].str.len() > 50]

df = df.reset_index(drop=True)
df.index.name = "id"


def clean_author(val) -> list[str]:
    if pd.isna(val):
        return [UNKNOWN_AUTHOR]

    raw = str(val).strip()

    if raw.startswith("By "):
        raw = raw[3:].strip()

    if not raw or raw.lower() == "by" or raw.endswith("%"):
        return [UNKNOWN_AUTHOR]

    normalized = re.sub(r",?\s*(?:and|&)\s*", ", ", raw)

    parts = [p.strip() for p in normalized.split(",") if p.strip()]

    if not parts:
        return [UNKNOWN_AUTHOR]

    if len(parts) == 1:
        return [parts[0]]

    cleaned_authors = []
    i = 0
    while i < len(parts):
        if i + 1 < len(parts):
            last_name = parts[i]
            first_name = parts[i + 1]
            cleaned_authors.append(f"{first_name} {last_name}".strip())
            i += 2
        else:
            cleaned_authors.append(parts[i])
            i += 1

    return cleaned_authors if cleaned_authors else [UNKNOWN_AUTHOR]


def clean_categories(val) -> list[str]:
    if pd.isna(val):
        return [UNKNOWN_GENRE]

    raw_category = str(val).strip()
    parts = re.split(r"[,&/]|\band\b", raw_category)

    clean_list = []
    for part in parts:
        item = part.strip()
        if len(item) > 2:
            clean_list.append(item.title())

    unique_genres = list(dict.fromkeys(clean_list))
    return unique_genres if unique_genres else [UNKNOWN_GENRE]


def extract_year(val) -> int | None:
    if pd.isna(val):
        return None

    match = re.search(r"\b(1[8-9]\d{2}|20[0-2]\d)\b", str(val))
    if match:
        return int(match.group(1))

    return None


df["authors"] = df["authors"].apply(clean_author)
df["genres"] = df["category"].apply(clean_categories)
df["year"] = df["publish date"].apply(extract_year).astype("Int64")

df = df[["title", "authors", "description", "genres", "year"]]
df = df.head(10000).copy()

df.to_csv("data/books.csv")
