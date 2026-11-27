
from pathlib import Path
import ast
import json
import joblib
import pandas as pd
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import save_npz

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "movies_metadata.csv"
OUTPUT_DIR = BASE_DIR / "movie_model"

OUTPUT_DIR.mkdir(exist_ok=True)

print("Reading movie dataset...")

df = pd.read_csv(
    CSV_PATH,
    usecols=[
        "id", "title", "overview", "genres",
        "tagline", "poster_path", "release_date",
        "vote_average"
    ],
    low_memory=False
)


# Parse genres using the same logic as main.py
def parse_genres(value):
    if isinstance(value, list):
        raw = value
    elif not isinstance(value, str) or not value.strip():
        return []
    else:
        try:
            raw = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            try:
                raw = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                return []

    return [
        item for item in raw
        if isinstance(item, dict)
    ] if isinstance(raw, list) else []


def genre_ids_from_value(value):
    ids = set()

    for genre in parse_genres(value):
        try:
            ids.add(int(genre.get("id")))
        except (TypeError, ValueError):
            continue

    return ids


# Clean IDs and titles
df["id"] = pd.to_numeric(df["id"], errors="coerce")
df = df.dropna(subset=["id", "title"]).copy()
df["id"] = df["id"].astype("int64")

df["title"] = df["title"].fillna("").astype(str).str.strip()
df["overview"] = df["overview"].fillna("").astype(str)
df["tagline"] = df["tagline"].fillna("").astype(str)

df = df.loc[df["title"] != ""]

# Keep one record per movie ID, preferring the longest overview
df["_overview_length"] = df["overview"].str.len()
df = df.sort_values("_overview_length", ascending=False)
df = df.drop_duplicates(subset=["id"], keep="first")
df = df.drop(columns=["_overview_length"]).reset_index(drop=True)

print(f"Movies after cleaning: {len(df)}")

# Store genre IDs as sets of integers
df["_genre_ids"] = df["genres"].apply(genre_ids_from_value)

# Use the same text combination as the recommendation model
texts = (
    df["overview"] + " " +
    df["tagline"] + " " +
    df["title"]
).tolist()

print("Training TF-IDF model...")

vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 1),
    min_df=2,
    max_features=40000,
    sublinear_tf=True,
    dtype=np.float32,
)

matrix = vectorizer.fit_transform(texts).tocsr()
matrix.sort_indices()

print("TF-IDF matrix shape:", matrix.shape)

print("Saving model files...")

joblib.dump(
    vectorizer,
    OUTPUT_DIR / "tfidf_vectorizer.joblib"
)

save_npz(
    OUTPUT_DIR / "tfidf_matrix.npz",
    matrix,
    compressed=True
)

df.to_pickle(OUTPUT_DIR / "movies_metadata.pkl")

print("\nModel building completed!")
print("Saved files:")

for file in OUTPUT_DIR.iterdir():
    print(f"{file.name}: {file.stat().st_size / (1024 * 1024):.2f} MB")
