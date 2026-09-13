import numpy as np


def calculate_ema_taste_vector(
    current_taste: list[float] | None, book_embedding: list[float], score: int
) -> list[float] | None:
    if score < 4:
        return current_taste

    book_vec = np.array(book_embedding, dtype=np.float32)

    if not current_taste:
        return book_vec.tolist()

    user_vec = np.array(current_taste, dtype=np.float32)
    alpha = 0.25 if score == 5 else 0.10

    new_vec = (1 - alpha) * user_vec + alpha * book_vec

    norm = np.linalg.norm(new_vec)
    if norm > 0:
        new_vec = new_vec / norm

    return new_vec.tolist()
