import html
import logging
import os
from typing import Any

import requests
import streamlit as st
from main import get_movie_trailer_id

# CONFIG
API_BASE = os.environ.get("BACKEND_API_URL", "https://cinevault-movie-recommention-1.onrender.com").rstrip("/")
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
REQUEST_TIMEOUT = (15, 60)  # connect timeout, read timeout
logger = logging.getLogger(__name__)

st.set_page_config(page_title="CineVault", page_icon="🎬", layout="wide")

# STATE + SESSION INITIALIZATION
if "view" not in st.session_state:
    st.session_state.view = "home"
if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""


# CINEMATIC STYLES
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Oswald:wght@500;600;700&display=swap');
:root{--red:#e50914;--red-dark:#b20710;--bg:#080808;--panel:#141414;--panel2:#1d1d1d;--text:#f5f5f1;--muted:#a3a3a3;--line:rgba(255,255,255,.10)}
*,*::before,*::after{box-sizing:border-box}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.stApp{background:radial-gradient(ellipse at 50% -20%,rgba(229,9,20,.20),transparent 45%),linear-gradient(180deg,#080808 0%,#101010 55%,#080808 100%);color:var(--text)}
.block-container{max-width:1500px;padding-top:1rem;padding-bottom:3rem}
[data-testid="stHeader"]{background:rgba(8,8,8,.88)}
[data-testid="stSidebar"]{background:#090909;border-right:1px solid var(--line)}
[data-testid="stSidebar"] *{color:var(--text)}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.7rem}
.sidebar-title{font-family:'Oswald',sans-serif;font-size:1.65rem;font-weight:700;letter-spacing:.08em;color:#fff;margin:.5rem 0}
.sidebar-title span{color:var(--red)}
.sidebar-rule{height:1px;background:var(--line);margin:.5rem 0 1rem}
.cinevault-hero{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.5rem 0 1.1rem;border-bottom:1px solid var(--line);margin-bottom:1.4rem}
.cinevault-logo{font-family:'Oswald',sans-serif;font-size:2.15rem;font-weight:700;letter-spacing:.06em;color:#fff;line-height:1}
.cinevault-logo span{color:var(--red)}
.cinevault-tagline{color:#bdbdbd;font-size:.82rem;letter-spacing:.04em;text-align:right}
.hero-panel{position:relative;overflow:hidden;border-radius:16px;min-height:235px;padding:2rem;background:linear-gradient(90deg,rgba(0,0,0,.94) 0%,rgba(0,0,0,.74) 52%,rgba(0,0,0,.25) 100%),radial-gradient(ellipse at 85% 50%,rgba(229,9,20,.35),transparent 55%),linear-gradient(135deg,#292929,#101010);border:1px solid rgba(255,255,255,.09);display:flex;flex-direction:column;justify-content:center;margin:.4rem 0 1.5rem}
.hero-kicker{color:#ff5a61;font-size:.72rem;font-weight:800;letter-spacing:.22em;text-transform:uppercase;margin-bottom:.65rem}
.hero-heading{font-family:'Oswald',sans-serif;font-size:clamp(2rem,5vw,3.5rem);font-weight:700;line-height:1.04;color:#fff;max-width:720px}
.hero-copy{color:#c5c5c5;font-size:.95rem;max-width:570px;margin-top:.75rem;line-height:1.6}
.section-label{font-family:'Oswald',sans-serif;font-size:1.45rem;font-weight:600;letter-spacing:.035em;color:#fff;margin:1.4rem 0 .85rem;display:flex;align-items:center;gap:.65rem}
.section-label:before{content:'';width:4px;height:1.2em;background:var(--red);border-radius:4px}
.stTextInput input{background:#202020!important;border:1px solid #373737!important;border-radius:7px!important;color:#fff!important;padding:.75rem 1rem!important;font-size:.95rem!important}
.stTextInput input:focus{border-color:#fff!important;box-shadow:0 0 0 1px #fff!important}
.stTextInput label,.stSelectbox label,.stSlider label{color:#bdbdbd!important;font-size:.78rem!important;font-weight:600!important}
.stSelectbox div[data-baseweb="select"]>div{background:#202020!important;border:1px solid #393939!important;border-radius:7px!important;color:#fff!important}
.stButton>button{background:var(--red)!important;color:#fff!important;border:0!important;border-radius:6px!important;font-weight:700!important;letter-spacing:.02em!important;min-height:2.45rem;transition:background .2s,transform .2s!important}
.stButton>button:hover{background:var(--red-dark)!important;transform:translateY(-1px)!important}
.stButton>button:focus{box-shadow:0 0 0 2px #fff!important}
.movie-details-link{display:flex;align-items:center;justify-content:center;width:100%;min-height:2.45rem;margin:.45rem 0 .2rem;padding:.55rem .75rem;background:var(--red);color:#fff!important;text-decoration:none!important;border-radius:6px;font-weight:700;letter-spacing:.02em;transition:background .2s,transform .2s}
.movie-details-link:hover{background:var(--red-dark);transform:translateY(-1px)}
.movie-details-link:focus{outline:2px solid #fff;outline-offset:2px}
hr{border-color:var(--line)!important}
.movie-card-wrap{margin-bottom:.8rem}
.movie-card{background:#171717;border:1px solid rgba(255,255,255,.07);border-radius:9px;overflow:hidden;transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease}
.movie-card:hover{transform:scale(1.035);border-color:rgba(255,255,255,.32);box-shadow:0 12px 30px rgba(0,0,0,.55)}
.movie-card img{width:100%;display:block;aspect-ratio:2/3;object-fit:cover;transition:filter .2s}
.movie-card:hover img{filter:brightness(1.08)}
.movie-card-body{padding:.55rem .65rem .35rem;min-height:68px}
.movie-card-title{font-size:.82rem;font-weight:700;line-height:1.35;color:#f5f5f5;min-height:2.5em;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.movie-card-rating{font-size:.74rem;color:#f5c518;margin-top:.3rem;font-weight:700}
.no-poster{background:linear-gradient(135deg,#292929,#101010);display:flex;align-items:center;justify-content:center;font-size:2.3rem;aspect-ratio:2/3}
.new-badge{position:absolute;top:9px;right:9px;background:var(--red);color:white;padding:3px 7px;border-radius:3px;font-size:.62rem;font-weight:800;z-index:2}
.detail-card{background:linear-gradient(145deg,#1b1b1b,#101010);border:1px solid var(--line);border-radius:14px;padding:1.6rem;box-shadow:0 18px 50px rgba(0,0,0,.35)}
.detail-title{font-family:'Oswald',sans-serif;font-size:clamp(2rem,4vw,3.2rem);font-weight:700;line-height:1.08;color:#fff}
.detail-meta{display:flex;gap:.5rem;flex-wrap:wrap;margin:.9rem 0}
.meta-chip{background:#292929;border:1px solid #414141;color:#eee;font-size:.72rem;font-weight:700;padding:4px 10px;border-radius:4px}
.meta-chip.red{background:rgba(229,9,20,.16);border-color:rgba(229,9,20,.45);color:#ff777d}
.detail-overview{font-size:.96rem;line-height:1.75;color:#c9c9c9;margin-top:1rem}
.detail-divider{height:1px;background:var(--line);margin:1.2rem 0}
.backdrop-wrap{border-radius:12px;overflow:hidden;margin:1rem 0 1.5rem;max-height:390px}
.backdrop-wrap img{width:100%;object-fit:cover;max-height:390px}
.poster-3d-wrap{border-radius:12px;overflow:hidden;box-shadow:0 14px 35px rgba(0,0,0,.5)}
.poster-3d img{width:100%;display:block}
.stAlert{background:#1b1b1b!important;border:1px solid var(--line)!important;color:#fff!important}
.stCaption{color:var(--muted)!important}
iframe{border-radius:10px}
@media(max-width:768px){.cinevault-hero{align-items:flex-start;flex-direction:column}.cinevault-tagline{text-align:left}.hero-panel{padding:1.35rem;min-height:200px}.detail-card{padding:1.1rem}.movie-card:hover{transform:none}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important}}
</style>
""",
    unsafe_allow_html=True,
)

# Query parameters routing
qp_view = st.query_params.get("view")
qp_id   = st.query_params.get("id")
if qp_view in ("home", "details"):
    st.session_state.view = qp_view
if qp_id:
    try:
        parsed_id = int(qp_id)
        if parsed_id > 0:
            st.session_state.selected_tmdb_id = parsed_id
            st.session_state.view = "details"
    except (TypeError, ValueError):
        pass


def goto_home():
    st.session_state.view = "home"
    st.query_params["view"] = "home"
    if "id" in st.query_params:
        del st.query_params["id"]
    st.rerun()


def goto_details(tmdb_id: int):
    st.session_state.view = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.query_params["view"] = "details"
    st.query_params["id"] = str(int(tmdb_id))
    st.rerun()


# API HELPERS
@st.cache_data(ttl=45, show_spinner=False)
def _api_get_json_cached(path: str, params_items: tuple):
    """
    Fetch and cache successful JSON responses only.
    Exceptions are deliberately raised so failed/time-out requests are not cached.
    """
    params = dict(params_items)
    url = f"{API_BASE}/{path.lstrip('/')}"
    last_error = None

    # Render free services may need time to wake from an idle state.
    # Retry once after a short pause if the request times out or temporarily fails.
    for attempt in range(2):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()

        except requests.Timeout as exc:
            last_error = exc
            logger.warning(
                "API timeout for %s (attempt %s/2)",
                path,
                attempt + 1,
            )

        except requests.RequestException as exc:
            last_error = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)

            # Retry transient server errors; don't retry normal client errors.
            if status is not None and status < 500:
                raise RuntimeError(f"The server returned HTTP {status}.")
            logger.warning(
                "API request failed for %s (attempt %s/2): %s",
                path,
                attempt + 1,
                exc,
            )

        except ValueError as exc:
            raise RuntimeError("The server returned an unexpected response.") from exc

        if attempt == 0:
            import time
            time.sleep(2)

    if isinstance(last_error, requests.Timeout):
        raise RuntimeError(
            "The server is taking too long to respond, even after a retry. "
            "Please try again in a moment."
        ) from last_error

    raise RuntimeError(
        "Could not connect to the CineVault server. Please try again."
    ) from last_error


def api_get_json(path: str, params: dict | None = None):
    """Fetch JSON from the CineVault backend with retry and readable errors."""
    try:
        # Sorting makes equivalent parameter dictionaries share the same cache key.
        params_items = tuple(sorted((params or {}).items()))
        return _api_get_json_cached(path, params_items), None
    except RuntimeError as exc:
        return None, str(exc)
    except Exception as exc:
        logger.exception("Unexpected API helper error for %s", path)
        return None, "An unexpected error occurred while contacting CineVault."




@st.cache_data(ttl=3600, show_spinner=False)
def cached_trailer_id(title: str):
    """Avoid repeating trailer lookups every time Streamlit reruns."""
    try:
        return get_movie_trailer_id(title)
    except Exception as exc:
        logger.warning("Trailer lookup failed for %r: %s", title, exc)
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def cached_valid_poster_url(url: str):
    """Return a poster URL only when the remote image actually responds."""
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        return None
    try:
        response = requests.get(url, timeout=(5, 10), stream=True)
        content_type = response.headers.get("Content-Type", "").lower()
        valid = response.ok and content_type.startswith("image/")
        response.close()
        return url if valid else None
    except requests.RequestException:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def cached_tmdb_poster_for_title(title: str):
    """Look up a fresh poster through the CineVault TMDB search endpoint."""
    try:
        data, error = api_get_json("/tmdb/search", params={"query": title})
        if error or not isinstance(data, dict):
            return None

        results = data.get("results") or []
        wanted = title.strip().casefold()

        # Prefer an exact title match with a poster; otherwise use the first
        # result that actually has a poster path.
        for movie in results:
            movie_title = str(movie.get("title") or "").strip().casefold()
            poster = clean_image_url(movie.get("poster_url") or movie.get("poster_path"))
            if movie_title == wanted and poster:
                return poster

        for movie in results:
            poster = clean_image_url(movie.get("poster_url") or movie.get("poster_path"))
            if poster:
                return poster
        return None
    except Exception as exc:
        logger.warning("TMDB poster lookup failed for %r: %s", title, exc)
        return None


def resolve_recommendation_posters(cards):
    """Validate recommendation posters and replace broken ones with TMDB matches."""
    resolved = []
    for card in cards:
        item = dict(card)
        poster = clean_image_url(item.get("poster_url"))
        if poster and cached_valid_poster_url(poster):
            item["poster_url"] = poster
        else:
            item["poster_url"] = cached_tmdb_poster_for_title(item.get("title", ""))
        resolved.append(item)
    return resolved


def safe_int(value: Any):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def clean_image_url(url):
    """Accept direct TMDB URLs, TMDB paths, and Markdown-wrapped URLs."""
    if not isinstance(url, str):
        return None
    url = url.strip()
    if url.startswith("[") and "](" in url:
        url = url.split("](", 1)[1].rsplit(")", 1)[0].strip()
    if url.startswith(("https://", "http://")):
        return url
    if url.startswith("/"):
        return f"https://image.tmdb.org/t/p/w500{url}"
    return None


def normalize_recommendations(items):
    """Normalize backend recommendation objects into the card format."""
    if isinstance(items, dict):
        items = items.get("results") or items.get("recommendations") or items.get("items") or []
    if not isinstance(items, list):
        return []

    cards = []
    for item in items:
        if not isinstance(item, dict):
            continue
        nested = item.get("tmdb") or item.get("movie") or item.get("movie_details") or {}
        if not isinstance(nested, dict):
            nested = {}

        movie_id = safe_int(
            nested.get("tmdb_id") or nested.get("id")
            or item.get("tmdb_id") or item.get("id")
        )
        title = (
            nested.get("title") or nested.get("name")
            or item.get("title") or item.get("name") or "Untitled"
        )
        poster = (
            nested.get("poster_url") or nested.get("poster_path")
            or item.get("poster_url") or item.get("poster_path")
        )
        rating = nested.get("vote_average", item.get("vote_average", ""))

        # Skip completely empty objects, but keep title-only cards visible.
        if title == "Untitled" and movie_id is None and not poster:
            continue
        cards.append({
            "tmdb_id": movie_id,
            "title": str(title),
            "poster_url": clean_image_url(poster),
            "vote_average": rating,
        })
    return cards


def poster_grid(cards, cols=6, key_prefix="grid"):
    if not cards:
        st.info("The API returned no displayable movie recommendations for this section.")
        return

    rows = (len(cards) + cols - 1) // cols
    idx  = 0

    for r in range(rows):
        colset = st.columns(cols, gap="small")
        for c in range(cols):
            if idx >= len(cards):
                break
            m       = cards[idx]; idx += 1
            tmdb_id = safe_int(m.get("tmdb_id") or m.get("id"))
            title   = str(m.get("title") or "Untitled")
            poster  = clean_image_url(m.get("poster_url"))
            rating  = m.get("vote_average", "")
            safe_title = html.escape(title)

            with colset[c]:
                st.markdown("<div class='movie-card-wrap'><div class='movie-card'>", unsafe_allow_html=True)

                if isinstance(poster, str) and poster.startswith(("https://", "http://")):
                    st.image(poster, use_container_width=True)
                else:
                    st.markdown("<div class='no-poster'>🎬</div>", unsafe_allow_html=True)

                rating_html = f"<div class='movie-card-rating'>★ {rating}</div>" if rating and rating != "N/A" else ""
                st.markdown(
                    f"""
                    <div class='movie-card-body'>
                        <div class='movie-card-title'>{safe_title}</div>
                        {rating_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if tmdb_id is not None:
                    # Navigate the top-level browser window in the SAME tab.
                    # The component button performs a real document navigation,
                    # so the new movie page starts at scroll position zero.
                    st.components.v1.html(
                        f"""
                        <button class="movie-details-link" type="button"
                          onclick="window.top.location.href = '?view=details&id={tmdb_id}'">
                          ▶ View details
                        </button>
                        <style>
                          .movie-details-link {{ display:flex; align-items:center; justify-content:center;
                            width:100%; min-height:42px; margin:7px 0 3px; padding:9px 12px;
                            background:#e50914; color:#fff; border:0; border-radius:6px;
                            font:700 14px Arial,sans-serif; cursor:pointer; }}
                          .movie-details-link:hover {{ background:#b20710; }}
                        </style>
                        """,
                        height=54,
                        scrolling=False,
                    )
                else:
                    st.button(
                        "▶ View details",
                        key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}",
                        disabled=True,
                    )

                st.markdown("</div></div>", unsafe_allow_html=True)


def to_cards_from_tfidf_items(tfidf_items):
    return normalize_recommendations(tfidf_items)


def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
    keyword_l = keyword.strip().lower()

    if isinstance(data, dict) and "results" in data:
        raw = data.get("results") or []
        raw_items = []
        for m in raw:
            title     = (m.get("title") or "").strip()
            tmdb_id   = m.get("id")
            poster_path = m.get("poster_path")
            tmdb_id = safe_int(tmdb_id)
            if not title or tmdb_id is None:
                continue
            raw_items.append({
                "tmdb_id":      tmdb_id,
                "title":        title,
                "poster_url":   f"{TMDB_IMG}{poster_path}" if poster_path else None,
                "release_date": m.get("release_date", ""),
                "vote_average": m.get("vote_average", "N/A"),
            })
    elif isinstance(data, list):
        raw_items = []
        for m in data:
            tmdb_id  = safe_int(m.get("tmdb_id") or m.get("id"))
            title    = (m.get("title") or "").strip()
            poster_url = m.get("poster_url")
            if not title or tmdb_id is None:
                continue
            raw_items.append({
                "tmdb_id":      tmdb_id,
                "title":        title,
                "poster_url":   poster_url,
                "release_date": m.get("release_date", ""),
                "vote_average": m.get("vote_average", "N/A"),
            })
    else:
        return [], []

    matched    = [x for x in raw_items if keyword_l in x["title"].lower()]
    final_list = matched if matched else raw_items
    suggestions = []
    for x in final_list[:10]:
        year  = (x.get("release_date") or "")[:4]
        label = f"{x['title']} ({year})" if year else x["title"]
        # Keep the TMDB id attached to each option, even when titles repeat.
        suggestions.append((label, x["tmdb_id"]))

    cards = [{
        "tmdb_id":      x["tmdb_id"],
        "title":        x["title"],
        "poster_url":   x["poster_url"],
        "vote_average": x.get("vote_average", "N/A"),
    } for x in final_list[:limit]]

    return suggestions, cards


# ==========================================================

# ==========================================================
# MAIN ROUTING LOGIC BLOCK
# ==========================================================
with st.sidebar:
    st.markdown("<div class='sidebar-title'>CINE<span>VAULT</span> 🎬</div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-rule'></div>", unsafe_allow_html=True)

    if st.button("🏠 Home"):
        goto_home()

    st.markdown("---")
    st.markdown("<div class='sidebar-rule'></div>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#7a7060;font-size:0.72rem;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:6px;'>Home Feed</p>",
        unsafe_allow_html=True,
    )
    home_category = st.selectbox(
        "Category",
        ["trending", "popular", "top_rated", "now_playing", "upcoming"],
        index=0,
        label_visibility="collapsed",
    )
    st.markdown(
        "<p style='color:#7a7060;font-size:0.72rem;letter-spacing:0.15em;text-transform:uppercase;margin:12px 0 6px;'>Columns</p>",
        unsafe_allow_html=True,
    )
    grid_cols = st.slider("Grid columns", 4, 8, 6, label_visibility="collapsed")

    st.markdown(
        """
        <div style='position:absolute;bottom:24px;left:0;right:0;text-align:center;'>
          <p style='color:#2a2a2a;font-size:0.65rem;letter-spacing:0.2em;'>CINEVAULT © 2026</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# CINEMATIC HERO HEADER
st.markdown(
    """
    <div class='cinevault-hero'>
      <a href='/?view=home' style='text-decoration:none;'>
        <div class='cinevault-logo'>CINE<span>VAULT</span></div>
      </a>
      <div class='cinevault-tagline'>Your next favourite movie starts here.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.view == "home":
    st.markdown(
        """
        <div class='hero-panel'>
          <div class='hero-kicker'>Unlimited stories · One destination</div>
          <div class='hero-heading'>FIND YOUR NEXT<br>GREAT WATCH.</div>
          <div class='hero-copy'>Explore trending hits, timeless favourites and hidden gems. Search the vault and discover what to watch next.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==========================================================
# ENGINE CORE: VIEW HOME
# ==========================================================
if st.session_state.view == "home":
    col_search, _, _ = st.columns([2, 1, 1])
    with col_search:
        typed = st.text_input(
            "SEARCH",
            placeholder="Search by title — Inception, Dune, The Godfather…",
            label_visibility="visible",
        )

    st.divider()

    # ── SEARCH MODE ──
    if typed.strip():
        if len(typed.strip()) < 2:
            st.caption("Type at least 2 characters for suggestions.")
        else:
            with st.spinner("Searching the vault…"):
                data, err = api_get_json("/tmdb/search", params={"query": typed.strip()})

            if err or data is None:
                st.error(f"Search failed: {err or 'No response from server.'}")
            else:
                suggestions, cards = parse_tmdb_search_to_cards(data, typed.strip(), limit=24)

                if suggestions:
                    labels   = ["— Select a movie —"] + [s[0] for s in suggestions]
                    selected_index = st.selectbox(
                        "Suggestions",
                        range(len(labels)),
                        index=0,
                        format_func=lambda i: labels[i],
                        label_visibility="collapsed",
                        key="movie_suggestion_index",
                    )
                    if selected_index > 0:
                        goto_details(suggestions[selected_index - 1][1])
                else:
                    st.info("No suggestions found. Try another keyword.")

                st.markdown(
                    "<div class='section-label'>Search Results</div>",
                    unsafe_allow_html=True,
                )
                if cards:
                    poster_grid(cards, cols=grid_cols, key_prefix="search_results")
                else:
                    st.info("No matching movies found. Try a different title.")

        st.stop()

    # ── HOME FEED ──
    cat_label = home_category.replace("_", " ").title()
    st.markdown(
        f"<div class='section-label'>{cat_label}</div>",
        unsafe_allow_html=True,
    )

    if "home_page" not in st.session_state:
        st.session_state.home_page = 1
    if "last_home_category" not in st.session_state:
        st.session_state.last_home_category = home_category
    if st.session_state.last_home_category != home_category:
        st.session_state.home_page = 1
        st.session_state.last_home_category = home_category

    with st.spinner("Loading the vault…"):
        home_data, err = api_get_json(
            "/home/paged",
            params={"category": home_category, "page": st.session_state.home_page, "limit": 24},
        )

    if err:
        st.error(f"Home feed failed: {err}")
        st.stop()
    if not isinstance(home_data, dict):
        st.error("The paginated home feed returned an unexpected response.")
        st.stop()

    home_cards = home_data.get("results") or []
    total_pages = int(home_data.get("total_pages") or 1)
    total_results = int(home_data.get("total_results") or 0)

    if not home_cards:
        st.info("No movies are available in this category right now. Please choose another category.")
        st.stop()

    st.caption(f"Page {st.session_state.home_page} of {total_pages:,} · {total_results:,} movies")
    poster_grid(home_cards, cols=grid_cols, key_prefix=f"home_feed_{home_category}_{st.session_state.home_page}")

    prev_col, page_col, next_col = st.columns([1, 2, 1])
    with prev_col:
        if st.button("← Previous", disabled=st.session_state.home_page <= 1, key="home_previous"):
            st.session_state.home_page -= 1
            st.rerun()
    with page_col:
        st.markdown(
            f"<div style='text-align:center;padding:.55rem 0;'>Page {st.session_state.home_page} / {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with next_col:
        if st.button("Next →", disabled=st.session_state.home_page >= total_pages, key="home_next"):
            st.session_state.home_page += 1
            st.rerun()

# ==========================================================
# ENGINE CORE: VIEW DETAILS
# ==========================================================
elif st.session_state.view == "details":
    tmdb_id = st.session_state.selected_tmdb_id
    if not tmdb_id:
        st.warning("No movie selected.")
        if st.button("← Back"):
            goto_home()
        st.stop()

    # Back button
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Back"):
            goto_home()

    # Load details
    with st.spinner("Loading…"):
        data, err = api_get_json(f"/movie/id/{tmdb_id}")

    if err or not isinstance(data, dict):
        st.error(f"Could not load details: {err or 'The server returned invalid movie details.'}")
        st.stop()

    # ── BACKDROP ──
    backdrop_url = clean_image_url(data.get("backdrop_url"))
    if backdrop_url:
        st.markdown("<div class='backdrop-wrap'>", unsafe_allow_html=True)
        st.image(backdrop_url, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── POSTER + DETAILS ──
    left, right = st.columns([1, 2.5], gap="large")

    with left:
        detail_poster_url = clean_image_url(data.get("poster_url"))
        if detail_poster_url:
            st.markdown("<div class='poster-3d-wrap'><div class='poster-3d'>", unsafe_allow_html=True)
            st.image(detail_poster_url, use_container_width=True)
            st.markdown("</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='no-poster' style='height:360px;border-radius:16px;'>🎬</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='detail-card'>", unsafe_allow_html=True)

        # Title
        safe_detail_title = html.escape(str(data.get("title") or "Untitled"))
        st.markdown(f"<div class='detail-title'>{safe_detail_title}</div>", unsafe_allow_html=True)

        # Meta chips
        release = (data.get("release_date") or "-")[:4]
        genres  = [str(g.get("name", "")) for g in data.get("genres", []) if isinstance(g, dict) and g.get("name")]
        rating  = data.get("vote_average")

        chips = ""
        if release and release != "-":
            chips += f"<span class='meta-chip'>{release}</span>"
        if rating is not None and rating != "":
            chips += f"<span class='meta-chip red'>★ {html.escape(str(rating))}</span>"
        for g in genres:
            chips += f"<span class='meta-chip'>{html.escape(g)}</span>"

        st.markdown(f"<div class='detail-meta'>{chips}</div>", unsafe_allow_html=True)
        st.markdown("<div class='detail-divider'></div>", unsafe_allow_html=True)

        # Overview
        overview = html.escape(str(data.get("overview") or "No overview available."))
        st.markdown(f"<div class='detail-overview'>{overview}</div>", unsafe_allow_html=True)
        
        # Define variable ahead of target block checks to prevent NameError mapping anomalies
        title = (data.get("title") or "").strip()

        # ── TRAILER ADDITION ──
        if title:
            with st.spinner("Fetching trailer..."):
                video_id = cached_trailer_id(title)
            
            if video_id:
                st.markdown("<div class='detail-divider'></div>", unsafe_allow_html=True)
                st.markdown("<p style='color:var(--gold); font-family:\"Bebas Neue\"; font-size:1.3rem; letter-spacing:1px;'>OFFICIAL TRAILER</p>", unsafe_allow_html=True)
                st.video(f"https://www.youtube.com/watch?v={video_id}")
        # ──────────────────────

        st.markdown("</div>", unsafe_allow_html=True)

    # ── CAST ──
    cast_members = data.get("cast") or []
    if cast_members:
        st.markdown("<div class='section-label'>Cast</div>", unsafe_allow_html=True)
        cast_cols = st.columns(6, gap="medium")
        for cast_index, member in enumerate(cast_members[:12]):
            if not isinstance(member, dict):
                continue
            with cast_cols[cast_index % 6]:
                profile_url = clean_image_url(member.get("profile_url"))
                if profile_url:
                    st.image(profile_url, use_container_width=True)
                else:
                    st.markdown(
                        "<div class='no-poster' style='aspect-ratio:2/3;font-size:1.5rem;'>🎭</div>",
                        unsafe_allow_html=True,
                    )
                actor_name = html.escape(str(member.get("name") or "Unknown actor"))
                character = html.escape(str(member.get("character") or ""))
                st.markdown(
                    f"<div class='movie-card-title'>{actor_name}</div>"
                    f"<div style='color:#aaa;font-size:.72rem;margin-top:3px;'>{character}</div>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── RECOMMENDATIONS ──
    if title:
        with st.spinner("Finding similar films..."):
            bundle, err2 = api_get_json(
                "/movie/search",
                params={
                    "query": title,
                    "tfidf_top_n": 12,
                    "genre_limit": 12
                }
            )

        if err2:
            st.warning(f"Could not load Similar Films: {err2}")

        elif isinstance(bundle, dict):

            tfidf_items = bundle.get("tfidf_recommendations", [])
            genre_items = bundle.get("genre_recommendations", [])

            st.markdown(
                "<div class='section-label'>Similar Films</div>",
                unsafe_allow_html=True
            )

            similar_cards = resolve_recommendation_posters(normalize_recommendations(tfidf_items))

            if similar_cards:
                poster_grid(
                    similar_cards,
                    cols=grid_cols,
                    key_prefix="details_tfidf"
                )
            else:
                st.warning("No TF-IDF movie cards were generated.")

            st.markdown(
                "<div class='section-label'>More Like This</div>",
                unsafe_allow_html=True
            )

            genre_cards = resolve_recommendation_posters(normalize_recommendations(genre_items))

            if genre_cards:
                poster_grid(
                    genre_cards,
                    cols=grid_cols,
                    key_prefix="details_genre"
                )
            else:
                st.info("No genre recommendations found.")

        else:
            st.warning("Unexpected recommendation API response.")

    else:
        st.warning("No title available to compute recommendations.")
