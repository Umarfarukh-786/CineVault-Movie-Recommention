import requests
import streamlit as st
from main import get_movie_trailer_id
# =============================
# CONFIG
# =============================
import os
API_BASE = os.environ.get("BACKEND_API_URL", "https://cinevault-movie-recommention.onrender.com")
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

st.set_page_config(page_title="CineVault", page_icon="🎬", layout="wide")

# =============================
# STATE + SESSION INITIALIZATION
# =============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "view" not in st.session_state:
    st.session_state.view = "home"
if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None

# =============================
# CINEMATIC STYLES
# =============================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:ital,wght@0,300;0,400;0,600;1,300&display=swap');

/* ── RESET & ROOT ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --gold:     #c9a84c;
  --gold2:    #f5d98b;
  --red:      #b01a1a;
  --red2:     #e52b2b;
  --bg:       #080808;
  --surface:  #101010;
  --surf2:    #161616;
  --border:   rgba(201,168,76,0.18);
  --text:     #e8e0d0;
  --muted:    #7a7060;
  --radius:   14px;
}

/* ── APP SHELL ── */
.stApp {
  background: var(--bg) !important;
  background-image:
    radial-gradient(ellipse 80% 40% at 50% 0%,   rgba(176,26,26,0.13) 0%, transparent 70%),
    radial-gradient(ellipse 60% 30% at 80% 80%,   rgba(201,168,76,0.07) 0%, transparent 60%),
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 3px,
      rgba(255,255,255,0.008) 3px,
      rgba(255,255,255,0.008) 4px
    ) !important;
  color: var(--text) !important;
  font-family: 'Barlow', sans-serif !important;
  font-weight: 300;
}

/* film-grain overlay */
.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
  opacity: 0.35;
  z-index: 9999;
  animation: grain 0.4s steps(1) infinite;
}

@keyframes grain {
  0%  { transform: translate(0, 0); }
  20% { transform: translate(-2px,  1px); }
  40% { transform: translate( 2px, -1px); }
  60% { transform: translate(-1px,  2px); }
  80% { transform: translate( 1px, -2px); }
 100% { transform: translate(0, 0); }
}

/* ── BLOCK CONTAINER ── */
.block-container {
  padding-top: 0.5rem !important;
  padding-bottom: 3rem !important;
  max-width: 1480px !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
  background: #090909 !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* ── HERO TITLE ── */
.cinevault-hero {
  text-align: center;
  padding: 2.5rem 0 1rem;
  position: relative;
}
.cinevault-logo {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(3.5rem, 8vw, 7rem);
  letter-spacing: 0.18em;
  line-height: 1;
  background: linear-gradient(135deg, var(--gold2) 0%, var(--gold) 45%, #8a6520 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 28px rgba(201,168,76,0.45));
  animation: logoGlow 4s ease-in-out infinite alternate;
  transition: all 0.35s ease;
  cursor: pointer;
}
.cinevault-logo:hover {
  transform: scale(1.04);
  filter:
    drop-shadow(0 0 18px rgba(201,168,76,0.8))
    drop-shadow(0 0 45px rgba(201,168,76,0.5));
  letter-spacing: 0.22em;
}
@keyframes logoGlow {
  from { filter: drop-shadow(0 0 18px rgba(201,168,76,0.30)); }
  to   { filter: drop-shadow(0 0 42px rgba(201,168,76,0.70)); }
}
.cinevault-tagline {
  font-family: 'Barlow', sans-serif;
  font-size: 0.78rem;
  letter-spacing: 0.55em;
  color: var(--muted);
  text-transform: uppercase;
  margin-top: 0.25rem;
}
.cinevault-rule {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 1.2rem auto 0;
  max-width: 600px;
}
.cinevault-rule span { flex: 1; height: 1px; background: linear-gradient(to right, transparent, var(--gold), transparent); }
.cinevault-rule em { font-style: normal; color: var(--gold); font-size: 1.1rem; }

/* ── SEARCH BOX ── */
.stTextInput input {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--border) !important;
  border-radius: 40px !important;
  color: var(--text) !important;
  font-family: 'Barlow', sans-serif !important;
  font-size: 1rem !important;
  padding: 0.7rem 1.4rem !important;
  transition: border 0.3s, box-shadow 0.3s;
}
.stTextInput input:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 3px rgba(201,168,76,0.15), 0 0 30px rgba(201,168,76,0.12) !important;
  outline: none !important;
}
.stTextInput label { color: var(--muted) !important; font-size: 0.75rem !important; letter-spacing: 0.12em !important; }

/* ── SELECTBOX ── */
.stSelectbox div[data-baseweb="select"] > div {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
}
.stSelectbox label { color: var(--muted) !important; font-size: 0.75rem !important; }

/* ── SLIDER ── */
.stSlider label { color: var(--muted) !important; font-size: 0.75rem !important; }

/* ── BUTTON ── */
.stButton > button {
  background: linear-gradient(135deg, var(--red) 0%, var(--red2) 100%) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 8px !important;
  font-family: 'Barlow', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.82rem !important;
  letter-spacing: 0.08em !important;
  padding: 0.45rem 0.9rem !important;
  width: 100% !important;
  transition: all 0.25s !important;
  box-shadow: 0 4px 18px rgba(176,26,26,0.35) !important;
  position: relative;
  overflow: hidden;
}
.stButton > button::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(120deg, transparent 30%, rgba(255,255,255,0.15) 50%, transparent 70%);
  transform: translateX(-100%);
  transition: transform 0.5s;
}
.stButton > button:hover::after { transform: translateX(100%); }
.stButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 28px rgba(229,43,43,0.5) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── DIVIDER ── */
hr { border-color: var(--border) !important; }

/* ── SECTION HEADINGS ── */
.section-label {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.5rem;
  letter-spacing: 0.22em;
  color: var(--gold);
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: 1.2rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--border);
}
.section-label::before { content: ''; display: block; width: 4px; height: 1.2em; background: var(--gold); border-radius: 2px; }

/* ── MOVIE CARD ── */
.movie-card-wrap { perspective: 900px; margin-bottom: 0.5rem; }
.movie-card {
  background: var(--surf2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  position: relative;
  transition: transform 0.35s cubic-bezier(.22,.68,0,1.2), box-shadow 0.35s;
  transform-style: preserve-3d;
  cursor: pointer;
}
.movie-card:hover {
  transform: rotateY(-5deg) rotateX(3deg) scale(1.045) translateZ(10px);
  box-shadow:
    8px 16px 40px rgba(0,0,0,0.7),
    0 0 0 1px var(--gold),
    inset 0 0 30px rgba(201,168,76,0.06);
}
.movie-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 55%;
  background: linear-gradient(180deg, rgba(255,255,255,0.07) 0%, transparent 100%);
  pointer-events: none;
  z-index: 2;
  border-radius: var(--radius) var(--radius) 0 0;
}
.movie-card img {
  width: 100%;
  display: block;
  border-radius: var(--radius) var(--radius) 0 0;
  transition: filter 0.3s;
}
.movie-card:hover img { filter: brightness(1.08) saturate(1.1); }
.movie-card-body { padding: 8px 10px 10px; }
.movie-card-title {
  font-family: 'Barlow', sans-serif;
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text);
  text-align: center;
  min-height: 2.6em;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 4px;
}
.movie-card-rating {
  text-align: center;
  font-size: 0.76rem;
  color: var(--gold);
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}

.no-poster {
  background: linear-gradient(135deg, #1a1a1a, #0d0d0d);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  height: 220px;
}

.new-badge {
  position: absolute;
  top: 10px; right: 10px;
  background: var(--red);
  color: #fff;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 2px 7px;
  border-radius: 4px;
  z-index: 3;
  box-shadow: 0 2px 10px rgba(176,26,26,0.6);
}

/* ── DETAILS PAGE ── */
.detail-card {
  background: linear-gradient(135deg, rgba(22,22,22,0.98), rgba(12,12,12,0.98));
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 2rem;
  position: relative;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(201,168,76,0.12);
}
.detail-card::after {
  content: '';
  position: absolute;
  top: -60px; right: -60px;
  width: 250px; height: 250px;
  background: radial-gradient(circle, rgba(201,168,76,0.08) 0%, transparent 70%);
  pointer-events: none;
}
.detail-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(2rem, 4vw, 3.2rem);
  letter-spacing: 0.1em;
  color: #fff;
  line-height: 1.05;
  text-shadow: 0 2px 20px rgba(0,0,0,0.8);
}
.detail-meta { display: flex; gap: 1rem; flex-wrap: wrap; margin: 0.8rem 0; }
.meta-chip {
  background: rgba(201,168,76,0.12);
  border: 1px solid rgba(201,168,76,0.25);
  color: var(--gold2);
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  padding: 3px 10px;
  border-radius: 20px;
  font-weight: 600;
  text-transform: uppercase;
}
.meta-chip.red {
  background: rgba(176,26,26,0.18);
  border-color: rgba(229,43,43,0.3);
  color: #ff6b6b;
}
.detail-overview {
  font-family: 'Barlow', sans-serif;
  font-size: 1rem;
  font-weight: 300;
  line-height: 1.75;
  color: #c0b8a8;
  margin-top: 1rem;
}
.detail-divider {
  height: 1px;
  background: linear-gradient(to right, var(--gold), transparent);
  margin: 1.2rem 0;
}

/* ── BACKDROP ── */
.backdrop-wrap {
  border-radius: 18px;
  overflow: hidden;
  position: relative;
  box-shadow: 0 10px 50px rgba(0,0,0,0.7);
  margin: 1.5rem 0;
}
.backdrop-wrap img { width: 100%; display: block; }
.backdrop-wrap::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(8,8,8,0.6) 0%, transparent 50%);
  pointer-events: none;
}

/* ── POSTER ── */
.poster-3d-wrap { perspective: 800px; }
.poster-3d {
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(201,168,76,0.3);
  box-shadow:
    16px 24px 60px rgba(0,0,0,0.8),
    -4px -4px 20px rgba(201,168,76,0.06),
    inset 0 1px 0 rgba(255,255,255,0.07);
  transform: rotateY(4deg) rotateX(-2deg);
  transition: transform 0.4s;
}
.poster-3d:hover { transform: rotateY(-2deg) rotateX(2deg) scale(1.02); }
.poster-3d img { width: 100%; display: block; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: var(--gold); }

h1, h2, h3 { color: var(--text) !important; }
.stMarkdown, .stMarkdown p { color: var(--text); }
p { color: var(--text); }
.stAlert { background: rgba(255,255,255,0.04) !important; border-color: var(--border) !important; color: var(--text) !important; }

/* ── SIDEBAR MENU TITLE ── */
.sidebar-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.4rem;
  letter-spacing: 0.25em;
  color: var(--gold);
  margin-bottom: 0.3rem;
}
.sidebar-rule { height: 1px; background: var(--border); margin: 0.6rem 0 1rem; }
.stSelectbox > div { color: var(--text) !important; }

/* ── CENTERED ACCOUNT GATE PANEL ── */
.auth-container {
  max-width: 450px;
  margin: 4rem auto;
  padding: 2.5rem;
  background: linear-gradient(135deg, #121212, #0d0d0d);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: 0 30px 70px rgba(0,0,0,0.9), 0 0 40px rgba(176,26,26,0.05);
}
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
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.view = "details"
    except:
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


# =============================
# API HELPERS
# =============================
@st.cache_data(ttl=30)
def api_get_json(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=65)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        return r.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"


def poster_grid(cards, cols=6, key_prefix="grid"):
    if not cards:
        st.info("No movies to show.")
        return

    rows = (len(cards) + cols - 1) // cols
    idx  = 0

    for r in range(rows):
        colset = st.columns(cols, gap="small")
        for c in range(cols):
            if idx >= len(cards):
                break
            m       = cards[idx]; idx += 1
            tmdb_id = m.get("tmdb_id")
            title   = m.get("title", "Untitled")
            poster  = m.get("poster_url")
            rating  = m.get("vote_average", "")

            with colset[c]:
                st.markdown("<div class='movie-card-wrap'><div class='movie-card'>", unsafe_allow_html=True)

                if poster:
                    st.image(poster, use_container_width=True)
                else:
                    st.markdown("<div class='no-poster'>🎬</div>", unsafe_allow_html=True)

                rating_html = f"<div class='movie-card-rating'>★ {rating}</div>" if rating and rating != "N/A" else ""
                st.markdown(
                    f"""
                    <div class='movie-card-body'>
                        <div class='movie-card-title'>{title}</div>
                        {rating_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button("▶ Open", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}"):
                    if tmdb_id:
                        goto_details(tmdb_id)

                st.markdown("</div></div>", unsafe_allow_html=True)


def to_cards_from_tfidf_items(tfidf_items):
    cards = []
    for x in tfidf_items or []:
        tmdb = x.get("tmdb") or {}
        if tmdb.get("tmdb_id"):
            cards.append({
                "tmdb_id":   tmdb["tmdb_id"],
                "title":     tmdb.get("title") or x.get("title") or "Untitled",
                "poster_url": tmdb.get("poster_url"),
            })
    return cards


def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
    keyword_l = keyword.strip().lower()

    if isinstance(data, dict) and "results" in data:
        raw = data.get("results") or []
        raw_items = []
        for m in raw:
            title     = (m.get("title") or "").strip()
            tmdb_id   = m.get("id")
            poster_path = m.get("poster_path")
            if not title or not tmdb_id:
                continue
            raw_items.append({
                "tmdb_id":      int(tmdb_id),
                "title":        title,
                "poster_url":   f"{TMDB_IMG}{poster_path}" if poster_path else None,
                "release_date": m.get("release_date", ""),
                "vote_average": m.get("vote_average", "N/A"),
            })
    elif isinstance(data, list):
        raw_items = []
        for m in data:
            tmdb_id  = m.get("tmdb_id") or m.get("id")
            title    = (m.get("title") or "").strip()
            poster_url = m.get("poster_url")
            if not title or not tmdb_id:
                continue
            raw_items.append({
                "tmdb_id":      int(tmdb_id),
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
        suggestions.append((label, x["tmdb_id"]))

    cards = [{
        "tmdb_id":      x["tmdb_id"],
        "title":        x["title"],
        "poster_url":   x["poster_url"],
        "vote_average": x.get("vote_average", "N/A"),
    } for x in final_list[:limit]]

    return suggestions, cards


# ==========================================================
# VIEW FUNCTION: AUTHENTICATION GATEWAY
# ==========================================================
def show_auth_page():
    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;font-family:\"Bebas Neue\";letter-spacing:2px;color:var(--gold);'>ACCOUNT PORTAL</h2>", unsafe_allow_html=True)
    
    tabs = st.tabs(["Login", "Sign Up"])
    
    with tabs[0]:
        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
        login_user = st.text_input("USERNAME", key="login_user")
        login_pass = st.text_input("PASSWORD", type="password", key="login_pass")
        
        if st.button("SIGN IN", type="primary", key="btn_login_submit"):
            if login_user.strip() and login_pass.strip():
                try:
                    response = requests.post(f"{API_BASE}/login", json={"username": login_user.strip(), "password": login_pass.strip()})
                    if response.status_code == 200:
                        st.session_state.logged_in = True
                        st.session_state.username = login_user.strip()
                        st.success("Access Granted. Loading the vault...")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")
                except Exception as e:
                    st.error(f"Backend offline or unreachable: {e}")
            else:
                st.warning("Please fill out all credentials.")

    with tabs[1]:
        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
        signup_email = st.text_input("EMAIL ADDRESS", placeholder="e.g., alex@example.com", key="signup_email")
        signup_user = st.text_input("CHOOSE USERNAME", placeholder="e.g., alex_vault", key="signup_user")
        signup_pass = st.text_input("CHOOSE PASSWORD", type="password", placeholder="Minimum 6 characters", key="signup_pass")
        
        if st.button("CREATE ACCOUNT", key="btn_signup_submit"):
            email_clean = signup_email.strip()
            user_clean = signup_user.strip()
            pass_clean = signup_pass.strip()
            
            if email_clean and user_clean and pass_clean:
                with st.spinner("Writing account to the vault..."):
                    try:
                        payload = {
                            "username": user_clean,
                            "email": email_clean,
                            "password": pass_clean
                        }
                        response = requests.post(f"{API_BASE}/signup", json=payload)
                        if response.status_code == 200:
                            st.success("🎉 Account created successfully! Please switch to the Login tab to sign in.")
                        else:
                            error_detail = response.json().get("detail", "Registration rejected.")
                            st.error(f"❌ Signup Failed: {error_detail}")
                    except Exception as e:
                        st.error(f"Backend connectivity failure: {e}")
            else:
                st.warning("⚠️ All input fields (Email, Username, and Password) are strictly required.")
                
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================================
# MAIN ROUTING LOGIC BLOCK
# ==========================================================
if not st.session_state.logged_in:
    show_auth_page()
else:
    # =============================
    # SIDEBAR PROFILE CONTROLS
    # =============================
    with st.sidebar:
        st.markdown("<div class='sidebar-title'>🎬 CineVault</div>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-rule'></div>", unsafe_allow_html=True)

        if st.button("🏠 Home"):
            goto_home()

        st.markdown("---")
        st.markdown(f"<p style='color:var(--text);font-size:0.85rem;margin-bottom:12px;'>User: <b>{st.session_state.username}</b></p>", unsafe_allow_html=True)
        if st.button("🔒 Logout", key="btn_logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
            
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

    # =============================
    # CINEMATIC HERO HEADER
    # =============================
    st.markdown(
        """
        <div class='cinevault-hero'>
          <a href='/?view=home' style='text-decoration:none;'>
            <div class='cinevault-logo'>CineVault</div>
          </a>
          <div class='cinevault-tagline'>Discover movies beyond imagination.</div>
          <div class='cinevault-rule'>
            <span></span><em>✦</em><span></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

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
                    st.error(f"Search failed: {err}")
                else:
                    suggestions, cards = parse_tmdb_search_to_cards(data, typed.strip(), limit=24)

                    if suggestions:
                        labels   = ["— Select a movie —"] + [s[0] for s in suggestions]
                        selected = st.selectbox("Suggestions", labels, index=0, label_visibility="collapsed")
                        if selected != "— Select a movie —":
                            label_to_id = {s[0]: s[1] for s in suggestions}
                            goto_details(label_to_id[selected])
                    else:
                        st.info("No suggestions found. Try another keyword.")

                    st.markdown(
                        "<div class='section-label'>Search Results</div>",
                        unsafe_allow_html=True,
                    )
                    poster_grid(cards, cols=grid_cols, key_prefix="search_results")

            st.stop()

        # ── HOME FEED ──
        cat_label = home_category.replace("_", " ").title()
        st.markdown(
            f"<div class='section-label'>{cat_label}</div>",
            unsafe_allow_html=True,
        )

        with st.spinner("Loading the vault…"):
            home_cards, err = api_get_json("/home", params={"category": home_category, "limit": 24})

        if err or not home_cards:
            st.error(f"Home feed failed: {err or 'Unknown error'}")
            st.stop()

        poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")

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

        if err or not data:
            st.error(f"Could not load details: {err or 'Unknown error'}")
            st.stop()

        # ── BACKDROP ──
        if data.get("backdrop_url"):
            st.markdown("<div class='backdrop-wrap'>", unsafe_allow_html=True)
            st.image(data["backdrop_url"], use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── POSTER + DETAILS ──
        left, right = st.columns([1, 2.5], gap="large")

        with left:
            if data.get("poster_url"):
                st.markdown("<div class='poster-3d-wrap'><div class='poster-3d'>", unsafe_allow_html=True)
                st.image(data["poster_url"], use_container_width=True)
                st.markdown("</div></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='no-poster' style='height:360px;border-radius:16px;'>🎬</div>", unsafe_allow_html=True)

        with right:
            st.markdown("<div class='detail-card'>", unsafe_allow_html=True)

            # Title
            st.markdown(f"<div class='detail-title'>{data.get('title','')}</div>", unsafe_allow_html=True)

            # Meta chips
            release = (data.get("release_date") or "-")[:4]
            genres  = [g["name"] for g in data.get("genres", [])]
            rating  = data.get("vote_average")

            chips = ""
            if release and release != "-":
                chips += f"<span class='meta-chip'>{release}</span>"
            if rating:
                chips += f"<span class='meta-chip red'>★ {rating}</span>"
            for g in genres:
                chips += f"<span class='meta-chip'>{g}</span>"

            st.markdown(f"<div class='detail-meta'>{chips}</div>", unsafe_allow_html=True)
            st.markdown("<div class='detail-divider'></div>", unsafe_allow_html=True)

            # Overview
            overview = data.get("overview") or "No overview available."
            st.markdown(f"<div class='detail-overview'>{overview}</div>", unsafe_allow_html=True)
            
            # Define variable ahead of target block checks to prevent NameError mapping anomalies
            title = (data.get("title") or "").strip()

            # ── TRAILER ADDITION ──
            if title:
                with st.spinner("Fetching trailer..."):
                    video_id = get_movie_trailer_id(title)
                
                if video_id:
                    st.markdown("<div class='detail-divider'></div>", unsafe_allow_html=True)
                    st.markdown("<p style='color:var(--gold); font-family:\"Bebas Neue\"; font-size:1.3rem; letter-spacing:1px;'>OFFICIAL TRAILER</p>", unsafe_allow_html=True)
                    st.video(f"https://www.youtube.com/watch?v={video_id}")
            # ──────────────────────

            st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        # ── RECOMMENDATIONS ──
        if title:
            with st.spinner("Finding similar films…"):
                bundle, err2 = api_get_json(
                    "/movie/search",
                    params={"query": title, "tfidf_top_n": 12, "genre_limit": 12},
                )

            if not err2 and bundle:
                st.markdown("<div class='section-label'>Similar Films</div>", unsafe_allow_html=True)
                poster_grid(
                    to_cards_from_tfidf_items(bundle.get("tfidf_recommendations")),
                    cols=grid_cols,
                    key_prefix="details_tfidf",
                )

                st.markdown("<div class='section-label'>More Like This</div>", unsafe_allow_html=True)
                poster_grid(
                    bundle.get("genre_recommendations", []),
                    cols=grid_cols,
                    key_prefix="details_genre",
                )
            else:
                st.info("Showing Genre recommendations (fallback).")
                with st.spinner("Loading fallback…"):
                    genre_only, err3 = api_get_json("/recommend/genre", params={"tmdb_id": tmdb_id, "limit": 18})
                if not err3 and genre_only:
                    st.markdown("<div class='section-label'>You May Also Like</div>", unsafe_allow_html=True)
                    poster_grid(genre_only, cols=grid_cols, key_prefix="details_genre_fallback")
                else:
                    st.warning("No recommendations available right now.")
        else:
            st.warning("No title available to compute recommendations.")