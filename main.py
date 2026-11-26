import os
import asyncio
import ast
import json
import re
import threading
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse, unquote

import bcrypt
import httpx
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from googleapiclient.discovery import build
from pydantic import BaseModel, EmailStr, Field

# =========================
# ENVIRONMENT
# =========================
load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_500 = "https://image.tmdb.org/t/p/w500"

if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY is missing. Set TMDB_API_KEY in Render environment variables.")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Set DATABASE_URL in Render environment variables.")


# =========================
# FASTAPI APP
# =========================
app = FastAPI(title="Movie Recommender API", version="3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# DATABASE SETUP
# =========================
def get_base_connection():
    """Connect to the MySQL server without selecting a database."""
    url = urlparse(DATABASE_URL)
    return pymysql.connect(
        host=url.hostname,
        user=url.username,
        password=unquote(url.password) if url.password else "",
        port=url.port or 3306,
        connect_timeout=15,
    )


def get_db_connection():
    """Connect to the application's MySQL database."""
    url = urlparse(DATABASE_URL)
    db_name = url.path.lstrip("/")
    if not db_name:
        raise RuntimeError("DATABASE_URL must include a database name.")

    return pymysql.connect(
        host=url.hostname,
        user=url.username,
        password=unquote(url.password) if url.password else "",
        database=db_name,
        port=url.port or 3306,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15,
    )


def init_db():
    """Create the application database and users table if they do not exist."""
    url = urlparse(DATABASE_URL)
    db_name = url.path.lstrip("/")
    if not db_name:
        raise RuntimeError("DATABASE_URL must include a database name.")

    # Database names cannot be passed as SQL parameters. Validate before interpolation.
    if not db_name.replace("_", "").isalnum():
        raise RuntimeError("DATABASE_URL contains an invalid database name.")

    base_conn = get_base_connection()
    try:
        with base_conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
        base_conn.commit()
    finally:
        base_conn.close()

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
        conn.commit()
    finally:
        conn.close()


# =========================
# LOCAL MOVIE DATASET / RECOMMENDATION MODEL
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOVIES_CSV_PATH = os.getenv(
    "MOVIES_CSV_PATH",
    os.path.join(BASE_DIR, "movies_metadata.csv"),
)

movies_df: Optional[pd.DataFrame] = None
movie_vectorizer: Optional[TfidfVectorizer] = None
movie_tfidf_matrix: Any = None
MOVIE_ID_TO_IDX: Dict[int, int] = {}
TITLE_TO_INDICES: Dict[str, List[int]] = {}

# Prevent duplicate model loads when multiple requests arrive together.
MOVIE_MODEL_LOAD_LOCK = threading.Lock()

# =========================
# PYDANTIC MODELS
# =========================
class SignupCredentials(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginCredentials(BaseModel):
    username: str
    password: str


class TMDBMovieCard(BaseModel):
    tmdb_id: int
    title: str
    poster_url: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: Optional[float] = None


class TMDBMovieDetails(BaseModel):
    tmdb_id: int
    title: str
    overview: Optional[str] = None
    release_date: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    genres: List[dict] = Field(default_factory=list)


class TFIDFRecItem(BaseModel):
    title: str
    score: float
    tmdb: Optional[TMDBMovieCard] = None


class SearchBundleResponse(BaseModel):
    query: str
    movie_details: TMDBMovieDetails
    tfidf_recommendations: List[TFIDFRecItem]
    genre_recommendations: List[TMDBMovieCard]
    # "local_csv_hybrid": generated from the local CSV using plot + genre similarity.
    # "tmdb_fallback": generated by TMDB similar/recommendation endpoints.
    # "none": neither source returned recommendations.
    recommendation_source: str = "none"


# =========================
# SECURITY HELPERS
# =========================
def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# =========================
# GENERAL HELPERS
# =========================
def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", str(title or "").strip().lower())


def make_img_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return f"{TMDB_IMG_500}{path}"


def get_movie_trailer_id(movie_title: str) -> Optional[str]:
    """Find an official trailer on YouTube when YOUTUBE_API_KEY is configured."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return None

    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        response = (
            youtube.search()
            .list(
                q=f"{movie_title} official trailer",
                part="id,snippet",
                maxResults=1,
                type="video",
            )
            .execute()
        )
        items = response.get("items", [])
        if items:
            return items[0]["id"]["videoId"]
    except Exception as exc:
        print(f"YouTube trailer lookup failed for {movie_title!r}: {exc}")

    return None


# =========================
# TMDB HELPERS
# =========================
async def tmdb_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Call TMDB with a small retry for transient connection failures."""
    request_params = dict(params)
    request_params["api_key"] = TMDB_API_KEY
    url = f"{TMDB_BASE}{path}"

    # A fresh connection is attempted on each retry. Keep environment proxy
    # settings enabled because they may be required by the local network.
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                response = await client.get(url, params=request_params)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as exc:
            print(f"TMDB returned HTTP {exc.response.status_code} for {path}.")
            raise HTTPException(
                status_code=502,
                detail=f"TMDB error {exc.response.status_code}: {exc.response.text}",
            )

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            print(
                f"TMDB connection attempt {attempt + 1}/3 failed for {path}: "
                f"{type(exc).__name__}: {repr(exc)}"
            )
            if attempt == 2:
                print("TMDB underlying cause:", repr(exc.__cause__))
                raise HTTPException(
                    status_code=502,
                    detail=f"TMDB connection failed after 3 attempts: {type(exc).__name__}",
                )
            await asyncio.sleep(1.0 * (attempt + 1))

        except httpx.RequestError as exc:
            print(f"TMDB request failed for {path}: {type(exc).__name__}: {repr(exc)}")
            raise HTTPException(
                status_code=502,
                detail=f"TMDB request error: {type(exc).__name__}",
            )


async def tmdb_cards_from_results(
    results: List[dict],
    limit: int = 20,
) -> List[TMDBMovieCard]:
    cards: List[TMDBMovieCard] = []

    for movie in (results or [])[:limit]:
        movie_id = movie.get("id")
        if not movie_id:
            continue

        cards.append(
            TMDBMovieCard(
                tmdb_id=int(movie_id),
                title=movie.get("title") or movie.get("name") or "Untitled",
                poster_url=make_img_url(movie.get("poster_path")),
                release_date=movie.get("release_date"),
                vote_average=movie.get("vote_average"),
            )
        )

    return cards


async def tmdb_movie_details(movie_id: int) -> TMDBMovieDetails:
    data = await tmdb_get(
        f"/movie/{movie_id}",
        {"language": "en-US"},
    )

    return TMDBMovieDetails(
        tmdb_id=int(data["id"]),
        title=data.get("title") or "",
        overview=data.get("overview"),
        release_date=data.get("release_date"),
        poster_url=make_img_url(data.get("poster_path")),
        backdrop_url=make_img_url(data.get("backdrop_path")),
        genres=data.get("genres") or [],
    )


async def tmdb_search_movies(query: str, page: int = 1) -> Dict[str, Any]:
    return await tmdb_get(
        "/search/movie",
        {
            "query": query,
            "include_adult": "false",
            "language": "en-US",
            "page": page,
        },
    )


async def tmdb_search_first(query: str) -> Optional[dict]:
    data = await tmdb_search_movies(query=query, page=1)
    results = data.get("results", [])
    return results[0] if results else None


async def attach_tmdb_card_by_title(title: str) -> Optional[TMDBMovieCard]:
    """Attach TMDB poster/details to a local TF-IDF recommendation."""
    try:
        movie = await tmdb_search_first(title)
        if not movie:
            return None

        return TMDBMovieCard(
            tmdb_id=int(movie["id"]),
            title=movie.get("title") or title,
            poster_url=make_img_url(movie.get("poster_path")),
            release_date=movie.get("release_date"),
            vote_average=movie.get("vote_average"),
        )
    except Exception as exc:
        print(f"Could not attach TMDB card for {title!r}: {exc}")
        return None


# =========================
# LOCAL CSV RECOMMENDATION HELPERS
# =========================
def parse_genres(value: Any) -> List[dict]:
    """Parse the dataset's genres column, stored as a JSON-like string."""
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
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def genre_ids_from_value(value: Any) -> set:
    ids = set()
    for genre in parse_genres(value):
        try:
            ids.add(int(genre.get("id")))
        except (TypeError, ValueError):
            continue
    return ids


def genre_ids_from_details(details: TMDBMovieDetails) -> set:
    ids = set()
    for genre in details.genres or []:
        try:
            ids.add(int(genre.get("id")))
        except (TypeError, ValueError):
            continue
    return ids


def movie_text(row: pd.Series) -> str:
    # Plot is the main signal. Tagline/title add a little context when available.
    parts = [
        str(row.get("overview") or ""),
        str(row.get("tagline") or ""),
        str(row.get("title") or ""),
    ]
    return " ".join(part.strip() for part in parts if part and part.strip())


def load_movie_dataset() -> None:
    """Load the CSV model once, on the first request that needs it."""
    global movies_df, movie_vectorizer, movie_tfidf_matrix

    if movies_df is not None and movie_vectorizer is not None and movie_tfidf_matrix is not None:
        return

    with MOVIE_MODEL_LOAD_LOCK:
        # Another request may have completed loading while this request waited.
        if movies_df is not None and movie_vectorizer is not None and movie_tfidf_matrix is not None:
            return
        _load_movie_dataset_unlocked()


def _load_movie_dataset_unlocked() -> None:
    """Read the CSV and build the reusable TF-IDF model."""
    global movies_df, movie_vectorizer, movie_tfidf_matrix
    global MOVIE_ID_TO_IDX, TITLE_TO_INDICES

    if not os.path.isfile(MOVIES_CSV_PATH):
        raise RuntimeError(
            f"Movie dataset not found: {MOVIES_CSV_PATH}. "
            "Place movies_metadata.csv beside main.py or set MOVIES_CSV_PATH."
        )

    data = pd.read_csv(MOVIES_CSV_PATH, low_memory=False)
    required = {"id", "title", "overview", "genres"}
    missing = required.difference(data.columns)
    if missing:
        raise RuntimeError(f"Movie dataset is missing required columns: {sorted(missing)}")

    data = data.copy()
    data["id"] = pd.to_numeric(data["id"], errors="coerce")
    data = data.dropna(subset=["id", "title"])
    data["id"] = data["id"].astype("int64")
    data["title"] = data["title"].fillna("").astype(str).str.strip()
    data["overview"] = data["overview"].fillna("").astype(str)
    if "tagline" not in data.columns:
        data["tagline"] = ""
    else:
        data["tagline"] = data["tagline"].fillna("").astype(str)
    data = data[data["title"] != ""]

    # The source has repeated IDs; keep the first usable row for each TMDB ID.
    data["_overview_length"] = data["overview"].str.len()
    data = data.sort_values("_overview_length", ascending=False)
    data = data.drop_duplicates(subset=["id"], keep="first").reset_index(drop=True)
    data["_genre_ids"] = data["genres"].apply(genre_ids_from_value)
    data["_text"] = data.apply(movie_text, axis=1)

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_features=40000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(data["_text"].tolist())

    id_to_idx = {int(movie_id): idx for idx, movie_id in enumerate(data["id"].tolist())}
    title_to_indices: Dict[str, List[int]] = {}
    for idx, title in enumerate(data["title"].tolist()):
        title_to_indices.setdefault(normalize_title(title), []).append(idx)

    movies_df = data
    movie_vectorizer = vectorizer
    movie_tfidf_matrix = matrix
    MOVIE_ID_TO_IDX = id_to_idx
    TITLE_TO_INDICES = title_to_indices
    print(
        f"Movie CSV loaded: {len(data)} unique TMDB IDs; "
        f"TF-IDF matrix shape: {matrix.shape}."
    )


def _local_movie_card(row: pd.Series) -> TMDBMovieCard:
    poster = row.get("poster_path")
    if pd.isna(poster):
        poster = None
    release_date = row.get("release_date")
    if pd.isna(release_date):
        release_date = None
    rating = row.get("vote_average")
    try:
        rating = float(rating) if not pd.isna(rating) else None
    except (TypeError, ValueError):
        rating = None
    return TMDBMovieCard(
        tmdb_id=int(row["id"]),
        title=str(row["title"]),
        poster_url=make_img_url(str(poster)) if poster else None,
        release_date=str(release_date) if release_date else None,
        vote_average=rating,
    )


def _rank_local_movies(
    query_overview: str,
    query_genres: set,
    limit: int = 12,
    exclude_tmdb_id: Optional[int] = None,
    local_query_idx: Optional[int] = None,
) -> List[Tuple[int, float]]:
    """Rank the full CSV using 60% plot similarity and 40% genre Jaccard."""
    load_movie_dataset()

    if local_query_idx is not None:
        query_vector = movie_tfidf_matrix[local_query_idx]
    else:
        query_vector = movie_vectorizer.transform([query_overview or ""])

    plot_scores = (query_vector @ movie_tfidf_matrix.T).toarray().ravel()
    candidate_genres = movies_df["_genre_ids"].tolist()
    genre_scores = np.zeros(len(movies_df), dtype=np.float32)
    if query_genres:
        for idx, candidate_ids in enumerate(candidate_genres):
            if candidate_ids:
                union = query_genres | candidate_ids
                genre_scores[idx] = len(query_genres & candidate_ids) / len(union) if union else 0.0

    final_scores = (0.60 * plot_scores) + (0.40 * genre_scores)
    if exclude_tmdb_id is not None:
        excluded_idx = MOVIE_ID_TO_IDX.get(int(exclude_tmdb_id))
        if excluded_idx is not None:
            final_scores[excluded_idx] = -1.0

    # Do not return records with neither plot nor genre information.
    valid_mask = (plot_scores > 0) | (genre_scores > 0)
    final_scores[~valid_mask] = -1.0
    ranked = np.argsort(-final_scores)

    results: List[Tuple[int, float]] = []
    for idx in ranked:
        if final_scores[idx] < 0:
            break
        row = movies_df.iloc[int(idx)]
        results.append((int(row["id"]), float(final_scores[idx])))
        if len(results) >= limit:
            break
    return results


def local_recommendations_for_title(title: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """Compatibility helper for the existing /recommend/tfidf endpoint."""
    load_movie_dataset()
    indices = TITLE_TO_INDICES.get(normalize_title(title), [])
    if not indices:
        raise HTTPException(status_code=404, detail=f"Title not found in local dataset: '{title}'")
    # If a title has multiple releases, use the row with the longest plot overview.
    query_idx = max(indices, key=lambda idx: len(str(movies_df.iloc[idx]["overview"])))
    query_row = movies_df.iloc[query_idx]
    query_genres = query_row["_genre_ids"]
    ranked = _rank_local_movies(
        query_overview=str(query_row["overview"]),
        query_genres=query_genres,
        limit=top_n,
        exclude_tmdb_id=int(query_row["id"]),
        local_query_idx=query_idx,
    )
    return [
        (str(movies_df.iloc[MOVIE_ID_TO_IDX[movie_id]]["title"]), score)
        for movie_id, score in ranked
    ]


async def hybrid_csv_recommendations(
    details: TMDBMovieDetails,
    limit: int = 12,
) -> List[TFIDFRecItem]:
    """Recommend from the local CSV, matching by TMDB ID before using TMDB plot text."""
    load_movie_dataset()
    local_idx = MOVIE_ID_TO_IDX.get(int(details.tmdb_id))
    query_overview = str(details.overview or "")
    query_genres = genre_ids_from_details(details)

    if local_idx is not None:
        local_row = movies_df.iloc[local_idx]
        query_overview = str(local_row["overview"] or query_overview)
        query_genres = local_row["_genre_ids"] or query_genres

    ranked = _rank_local_movies(
        query_overview=query_overview,
        query_genres=query_genres,
        limit=limit,
        exclude_tmdb_id=int(details.tmdb_id),
        local_query_idx=local_idx,
    )

    items: List[TFIDFRecItem] = []
    for movie_id, score in ranked:
        idx = MOVIE_ID_TO_IDX[movie_id]
        row = movies_df.iloc[idx]
        card = _local_movie_card(row)
        items.append(TFIDFRecItem(title=card.title, score=score, tmdb=card))
    return items


# =========================
# TMDB FALLBACK RECOMMENDATIONS
# =========================
async def get_tmdb_fallback_recommendations(
    tmdb_id: int,
    limit: int,
) -> List[TMDBMovieCard]:
    """
    Try TMDB's movie-specific recommendations first, then its similar movies
    endpoint. Return an empty list only if both endpoints provide no results.
    """
    fallback_paths = [
        f"/movie/{tmdb_id}/recommendations",
        f"/movie/{tmdb_id}/similar",
    ]

    for path in fallback_paths:
        try:
            data = await tmdb_get(
                path,
                {
                    "language": "en-US",
                    "page": 1,
                },
            )

            cards = await tmdb_cards_from_results(
                data.get("results", []),
                limit=limit,
            )

            cards = [
                card for card in cards
                if card.tmdb_id != tmdb_id
            ]

            if cards:
                print(
                    f"TMDB fallback returned {len(cards)} movies "
                    f"for movie ID {tmdb_id} using {path}."
                )
                return cards

        except HTTPException as exc:
            print(f"TMDB fallback endpoint {path} failed: {exc.detail}")
        except Exception as exc:
            print(f"Unexpected TMDB fallback error for {path}: {exc}")

    return []


# The local CSV/TF-IDF model is intentionally NOT loaded at startup.
# It is loaded on demand by the recommendation functions above.


# =========================
# BASIC ROUTES
# =========================
@app.get("/")
def read_root():
    return {"message": "CineVault API is running successfully!"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "movie_dataset_loaded": movies_df is not None and movie_tfidf_matrix is not None,
        "movie_count": len(movies_df) if movies_df is not None else 0,
    }


# =========================
# AUTHENTICATION ROUTES
# =========================
@app.post("/signup")
def signup(user: SignupCredentials):
    username = user.username.strip()
    email = str(user.email).strip()
    password = user.password.strip()

    if not username or not email or not password:
        raise HTTPException(
            status_code=400,
            detail="All signup fields are required.",
        )

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE username = %s",
                (username,),
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Username already exists!",
                )

            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (email,),
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="An account with this email already exists!",
                )

            password_hash = hash_password(password)

            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
                """,
                (username, email, password_hash),
            )

        connection.commit()

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database execution failure: {exc}",
        )
    finally:
        connection.close()

    return {"message": "User registered successfully!"}


@app.post("/login")
def login(user: LoginCredentials):
    username = user.username.strip()
    password = user.password.strip()

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failure: {exc}",
        )
    finally:
        connection.close()

    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    return {
        "message": "Login successful",
        "username": username,
    }


# =========================
# HOME FEED
# =========================
@app.get("/home", response_model=List[TMDBMovieCard])
async def home(
    category: str = Query("popular"),
    limit: int = Query(24, ge=1, le=50),
):
    if category == "trending":
        data = await tmdb_get(
            "/trending/movie/day",
            {"language": "en-US"},
        )
    elif category in {"popular", "top_rated", "upcoming", "now_playing"}:
        data = await tmdb_get(
            f"/movie/{category}",
            {
                "language": "en-US",
                "page": 1,
            },
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid category. Use popular, top_rated, upcoming, now_playing, or trending.",
        )

    return await tmdb_cards_from_results(
        data.get("results", []),
        limit=limit,
    )


# =========================
# TMDB SEARCH
# =========================
@app.get("/tmdb/search")
async def tmdb_search(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1, le=10),
):
    return await tmdb_search_movies(
        query=query,
        page=page,
    )


# =========================
# MOVIE DETAILS
# =========================
@app.get("/movie/id/{tmdb_id}", response_model=TMDBMovieDetails)
async def movie_details_route(tmdb_id: int):
    return await tmdb_movie_details(tmdb_id)


# =========================
# GENRE RECOMMENDATIONS
# =========================
@app.get("/recommend/genre", response_model=List[TMDBMovieCard])
async def recommend_genre(
    tmdb_id: int = Query(...),
    limit: int = Query(18, ge=1, le=50),
):
    details = await tmdb_movie_details(tmdb_id)

    if not details.genres:
        return []

    genre_id = details.genres[0]["id"]

    discover = await tmdb_get(
        "/discover/movie",
        {
            "with_genres": genre_id,
            "language": "en-US",
            "sort_by": "popularity.desc",
            "page": 1,
        },
    )

    cards = await tmdb_cards_from_results(
        discover.get("results", []),
        limit=limit,
    )

    return [
        card for card in cards
        if card.tmdb_id != tmdb_id
    ]


# =========================
# TF-IDF RECOMMENDATIONS ONLY
# =========================
@app.get("/recommend/tfidf")
async def recommend_tfidf(
    title: str = Query(..., min_length=1),
    top_n: int = Query(10, ge=1, le=50),
):
    recommendations = local_recommendations_for_title(
        title,
        top_n=top_n,
    )

    return [
        {
            "title": title,
            "score": score,
        }
        for title, score in recommendations
    ]


# =========================
# SEARCH BUNDLE
# Movie details + Similar Films + Genre recommendations
# =========================
@app.get("/movie/search", response_model=SearchBundleResponse)
async def search_bundle(
    query: str = Query(..., min_length=1),
    tfidf_top_n: int = Query(12, ge=1, le=30),
    genre_limit: int = Query(12, ge=1, le=30),
):
    # Resolve the selected movie through TMDB, then rank the complete local CSV.
    best_match = await tmdb_search_first(query)
    if not best_match:
        raise HTTPException(status_code=404, detail=f"No TMDB movie found for query: {query}")

    tmdb_id = int(best_match["id"])
    details = await tmdb_movie_details(tmdb_id)

    # Similar Films now uses the local 45K-movie CSV model, not the old pickle files.
    tfidf_items = await hybrid_csv_recommendations(details, limit=tfidf_top_n)
    recommendation_source = "local_csv_hybrid" if tfidf_items else "tmdb_fallback"

    # Keep the existing independent genre-recommendation section and response shape.
    genre_recommendations: List[TMDBMovieCard] = []
    if details.genres:
        genre_id = details.genres[0]["id"]
        discover = await tmdb_get(
            "/discover/movie",
            {
                "with_genres": genre_id,
                "language": "en-US",
                "sort_by": "popularity.desc",
                "page": 1,
            },
        )
        genre_cards = await tmdb_cards_from_results(discover.get("results", []), limit=genre_limit)
        genre_recommendations = [card for card in genre_cards if card.tmdb_id != details.tmdb_id]

    # Fallback only if local CSV ranking has no usable candidates.
    if not tfidf_items:
        fallback_cards = await get_tmdb_fallback_recommendations(tmdb_id=tmdb_id, limit=tfidf_top_n)
        tfidf_items = [
            TFIDFRecItem(title=card.title, score=0.0, tmdb=card)
            for card in fallback_cards
        ]
        recommendation_source = "tmdb_fallback" if fallback_cards else "none"

    return SearchBundleResponse(
        query=query,
        movie_details=details,
        tfidf_recommendations=tfidf_items,
        genre_recommendations=genre_recommendations,
        recommendation_source=recommendation_source,
    )


# =========================
# LOCAL DEVELOPMENT ENTRY POINT
# =========================
if __name__ == "__main__":
    import uvicorn

    # Initialize the database only when running this file directly.
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as exc:
        print(f"Database initialization skipped/failed: {exc}")

    # Launch the local development server.
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )

