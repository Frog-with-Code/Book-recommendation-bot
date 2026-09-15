# 📚 Graph-Based Book Recommendation Telegram Bot

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-008CC1?style=flat&logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Architecture](https://img.shields.io/badge/Architecture-Clean%20%2F%20DDD-brightgreen?style=flat)](#-project-architecture)

An intelligent Telegram bot for personalized book recommendations powered by the **Neo4j graph database**, **semantic vector embeddings**, and **Clean Architecture / Domain-Driven Design (DDD)** principles.

Instead of relying on generic bestseller lists, the bot analyzes deep plot narratives, builds an evolving reading graph for each user, and adapts to user feedback in real time.

---

## 🌟 Key Features

- **Hybrid Search (Recall & Re-ranking):** 
  A two-stage recommendation pipeline: fast candidate generation using an HNSW vector index over book descriptions (Recall) followed by multi-factor graph traversal scoring (Re-ranking).
- **Dynamic Taste Profile (EMA Taste Vector):** 
  The user profile is not computed from scratch on every interaction. Instead, it smoothly evolves with each high rating using an Exponential Moving Average (EMA) formula with L2 normalization.
- **Zero-Centered Feedback Scoring:** 
  Ratings are normalized around a neutral baseline (`score - 3`), allowing the algorithm to seamlessly reward beloved authors/genres while penalizing disliked ones.
- **Literary Era Proximity:** 
  Awards bonus points when a book matches the reader's preferred publication era ($\pm 10$ years from previously enjoyed titles) without skewing tastes via a naive "average year".
- **Interactive Onboarding (FSM):** 
  Solves the Cold Start problem through an interactive multi-step questionnaire: choosing macro-genres via inline buttons and describing the desired plot in free-form natural language.
- **Anti-Filter Bubble Fallback (Exploration):** 
  If an active reader has read all books in their immediate semantic cluster, the fallback engine expands their horizons using proven graph connections instead of falling back to random picks.
- **Explainable AI (Transparent Cards):** 
  Every recommendation comes with an itemized breakdown explaining *why* it was chosen (plot similarity percentage, favorite author, matching genres, and era alignment).

---

## 🧠 Graph Data Model

The core knowledge engine is built on **Neo4j**, representing entities and interactions as nodes and relationships:

```text
 (User) ────[:LIKES_GENRE]────> (Genre) <────[:HAS_GENRE]──── (Book)
   │                                                            │
   │                                                            │ [:WRITTEN_BY]
   │                                                            ▼
   └───────[:RATED {score: 1-5}]────────> (Book) ────────> (Author)
```

- **Nodes:**
  - `:User` — `id`, `username`, `taste_embedding` (768-dim float vector), `last_active_at`.
  - `:Book` — `id`, `title`, `description`, `year`, `embedding` (768-dim float vector).
  - `:Author` — `name`.
  - `:Genre` — `name`.
- **Relationships:**
  - `(:Book)-[:WRITTEN_BY]->(:Author)`
  - `(:Book)-[:HAS_GENRE]->(:Genre)`
  - `(:User)-[:LIKES_GENRE]->(:Genre)` (Explicit onboarding preferences)
  - `(:User)-[:RATED {score, created_at, updated_at}]->(:Book)` (Rating history)

---

## 🏛 Project Architecture

The codebase strictly adheres to **Clean Architecture** with inward-pointing dependencies:

```text
book_recommendation_bot/
├── data/                       # CSV datasets (mounted via Docker volume, not baked into image)
├── scripts/                    # ETL scripts for cleaning and batch ingestion
│   └── import_books.py         # Vectorization and batched Neo4j loading
├── src/
│   ├── book_recommendation_bot/
│   │   ├── domain/             # Core business entities (Book, User, BookScore)
│   │   ├── application/        # Use cases, application services, and repository ports
│   │   │   ├── services.py     # Recommendation orchestration & EMA math
│   │   │   ├── interfaces.py   # Abstract ports (UserRepository, BookRepository)
│   │   │   └── exceptions.py   # Domain exceptions
│   │   ├── infrastructure/     # External adapters
│   │   │   ├── repositories.py # Production Cypher queries (Recall & Re-ranking)
│   │   │   └── embeddings.py   # Embedding inference service (SentenceTransformers)
│   │   └── presentation/       # Telegram UI layer (aiogram)
│   │       ├── handlers.py     # Command & callback handlers (/start, /recommend, /search, /genres)
│   │       ├── keyboards.py    # Inline keyboards and star rating controls
│   │       ├── middlewares.py  # User context and safety middlewares
│   │       ├── states.py       # FSM dialog state groups
│   │       └── utils.py        # HTML card formatting with explainable reasoning
│   └── config.py               # Strongly typed settings via Pydantic Settings
├── Dockerfile                  # Multi-layer, cache-optimized bot image
├── docker-compose.yml          # Container orchestration for Neo4j and Bot
├── requirements.txt            # Python dependencies
└── .dockerignore               # Build context filter (excludes .venv, data, caches)
```

---

## 🛠 Tech Stack

- **Language:** Python 3.12
- **Telegram Bot Framework:** `aiogram 3.x` (FSM, Routers, Middlewares, HTML formatting)
- **Database:** Neo4j 5 Community Edition
- **Vector Search:** Neo4j Native HNSW Vector Index (Cosine Similarity)
- **Embedding Models:** `nomic-ai/nomic-embed-text-v1.5` / `BAAI/bge-base-en-v1.5` (768 dimensions)
- **Data Processing & ML:** `NumPy`, `Pandas`, `PyTorch`, `Sentence-Transformers`
- **Configuration:** `pydantic-settings`
- **DevOps:** Docker, Docker Compose, Buildx (isolated network, healthcheck, volume caching)

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/book-recommendation-bot.git
cd book-recommendation-bot
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```env
BOT_TOKEN=your_bot_token
NEO4J_PASSWORD=your_secret_password
```

### 3. Start the Database

Launch the Neo4j container:

```bash
docker compose up -d neo4j
```

Wait until the service status reports `healthy`:
```bash
docker compose ps
```

### 4. Initialize Database Constraints & Vector Index

Open **Neo4j Browser** (`http://localhost:7474`), log in (`neo4j` / your password), and execute:

```cypher
// Uniqueness constraints
CREATE CONSTRAINT book_id_unique IF NOT EXISTS FOR (b:Book) REQUIRE b.id IS UNIQUE;
CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT genre_name_unique IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE;
CREATE CONSTRAINT author_name_unique IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE;

// 768-dimensional HNSW vector index for plot descriptions
CREATE VECTOR INDEX book_embeddings IF NOT EXISTS
FOR (b:Book) ON (b.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};
```

### 5. Ingest the Book Dataset

Place your cleaned `books.csv` file into the `data/` folder and run the batch vectorization script inside Docker:

```bash
docker compose run --rm bot python -m scripts.import_books
```
*This downloads the embedding model into `./hf_cache`, encodes descriptions on CPU with progress tracking, and merges books into Neo4j in batches of 500.*

### 6. Start the Telegram Bot

Start the bot container in the background:

```bash
docker compose up -d bot
```

View real-time logs:
```bash
docker compose logs -f bot
```

---

## 🤖 Telegram Bot Commands

| Command | Description |
| :--- | :--- |
| **`/start`** | Greets returning users or initiates the 2-step onboarding flow for newcomers (macro-genres + desired plot prompt). |
| **`/recommend`** | Delivers a personalized book recommendation with an explainability breakdown and star rating buttons (1–5★). |
| **`/search`** | Semantic search by natural language plot description without overriding the user's permanent taste vector. |
| **`/genres`** | View and update favorite genres with dynamic graph updates. |

---

## 📐 Scoring Formula (Re-ranking)

For each candidate retrieved by the HNSW vector search, the final score is calculated as:

$$\text{Total Score} = \text{Vector Score} + \text{Author Impact} + \text{Genre Onboarding} + \text{Genre Experience} + \text{Era Score}$$

- **`Vector Score`** $\in [0.0; +1.0]$: Cosine similarity between the active taste vector and the book description.
- **`Author Impact`** $\in [-0.25; +0.25]$: Mean deviation of the author's previous ratings: $\text{avg}(\text{score} - 3) \times 0.15$.
- **`Genre Onboarding`** $\in [0.0; +0.30]$: Fixed bonus for genres selected during onboarding ($+0.15$ per matching genre).
- **`Genre Experience`** $\in [-0.20; +0.20]$: Historical feedback for this genre: $\text{avg}(\text{score} - 3) \times 0.10$.
- **`Era Score`** $\in [0.0; 0.10]$: Proximity bonus for books published within $\pm 10$ years of previously enjoyed titles.