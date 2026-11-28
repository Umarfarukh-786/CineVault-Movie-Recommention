from concurrent.futures import ThreadPoolExecutor
import html
import logging
import os
from typing import Any
from urllib.parse import quote_plus

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
.block-container{max-width:1500px;padding-top:2rem;padding-bottom:3rem}
/* Remove Streamlit's toolbar/header so it cannot overlap the CineVault brand */
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebar"],[data-testid="stSidebarNav"]{display:none!important}
header{visibility:hidden!important;height:0!important}

[data-testid="stSidebar"]{background:#090909;border-right:1px solid var(--line)}
[data-testid="stSidebar"] *{color:var(--text)}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.7rem}
.sidebar-title{font-family:'Oswald',sans-serif;font-size:1.65rem;font-weight:700;letter-spacing:.08em;color:#fff;margin:.5rem 0}
.sidebar-title span{color:var(--red)}
.sidebar-rule{height:1px;background:var(--line);margin:.5rem 0 1rem}
.cinevault-hero{position:relative;display:flex;align-items:center;justify-content:space-between;gap:1.2rem;padding:1.05rem 1.35rem;margin:0 0 1.35rem;border:1px solid rgba(255,255,255,.10);border-radius:18px;background:linear-gradient(110deg,rgba(255,255,255,.075),rgba(255,255,255,.018) 58%,rgba(229,9,20,.09));backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);box-shadow:0 12px 38px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.08);overflow:hidden}
.cinevault-hero:after{content:"";position:absolute;right:12%;top:-90px;width:270px;height:180px;background:rgba(229,9,20,.15);filter:blur(75px);pointer-events:none}
.cinevault-logo{font-family:'Oswald',sans-serif;font-size:2.35rem;font-weight:700;letter-spacing:.075em;color:#fff;line-height:1;text-shadow:0 4px 22px rgba(0,0,0,.35)}
.cinevault-logo span{color:#f32635}
.cinevault-tagline{color:#d2d2d7;font-size:.8rem;letter-spacing:.055em;text-align:right}
.home-hero-panel{position:relative;isolation:isolate;overflow:hidden;border:1px solid rgba(255,255,255,.12);border-radius:25px;min-height:270px;padding:clamp(1.5rem,4vw,3.2rem);margin:.2rem 0 1.5rem;background:radial-gradient(ellipse at 82% 40%,rgba(229,9,20,.24),transparent 37%),radial-gradient(ellipse at 100% 100%,rgba(115,22,36,.2),transparent 44%),linear-gradient(115deg,#171719 0%,#101012 52%,#190d10 100%);box-shadow:0 24px 65px rgba(0,0,0,.38),inset 0 1px 0 rgba(255,255,255,.08)}
.home-hero-panel:before{content:"";position:absolute;z-index:-1;inset:0;background:linear-gradient(90deg,rgba(0,0,0,.25),transparent 75%);pointer-events:none}
.home-hero-panel:after{content:"C";position:absolute;z-index:-1;right:5%;top:50%;transform:translateY(-56%);font-family:'Oswald',sans-serif;font-size:clamp(13rem,28vw,24rem);font-weight:700;line-height:.8;color:rgba(255,255,255,.025);text-shadow:0 0 65px rgba(229,9,20,.12);pointer-events:none}
.home-hero-kicker{display:inline-flex;align-items:center;gap:.55rem;color:#ff777e;font-size:.68rem;font-weight:800;letter-spacing:.24em;text-transform:uppercase;margin-bottom:.85rem}
.home-hero-kicker:before{content:"";width:25px;height:2px;background:#ed2935;border-radius:4px}
.home-hero-title{font-family:'Oswald',sans-serif;font-size:clamp(2.35rem,5.3vw,4.5rem);font-weight:700;line-height:.98;letter-spacing:-.015em;color:#fff;max-width:790px;text-shadow:0 5px 28px rgba(0,0,0,.4)}
.home-hero-title span{color:#f02a37}
.home-hero-copy{color:#c5c5ca;font-size:.96rem;line-height:1.7;max-width:590px;margin-top:1rem}
.home-search-label{color:#f0f0f2;font-size:.72rem;font-weight:800;letter-spacing:.17em;text-transform:uppercase;margin:.15rem 0 .4rem}
.home-search-row{position:relative;max-width:900px;margin-top:1.25rem;padding:.45rem;border:1px solid rgba(255,255,255,.17);border-radius:15px;background:rgba(8,8,10,.58);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);box-shadow:0 14px 35px rgba(0,0,0,.32),inset 0 1px 0 rgba(255,255,255,.08)}
.home-search-row [data-testid="stTextInput"]{margin:0}
.home-search-row [data-testid="stTextInput"] label{display:none}
.home-search-row [data-testid="stTextInput"] input{height:3.25rem!important;background:rgba(255,255,255,.055)!important;border:1px solid rgba(255,255,255,.08)!important;border-radius:10px!important;padding:0 1.1rem!important;color:#fff!important;font-size:1rem!important;box-shadow:none!important}
.home-search-row [data-testid="stTextInput"] input:focus{border-color:rgba(255,95,105,.75)!important;box-shadow:0 0 0 3px rgba(229,9,20,.14)!important}
.home-search-row [data-testid="stTextInput"] input::placeholder{color:#92929a!important}
@media(max-width:700px){.cinevault-hero{padding:.9rem 1rem;align-items:flex-start;flex-direction:column}.cinevault-logo{font-size:2rem}.cinevault-tagline{text-align:left}.home-hero-panel{min-height:250px;border-radius:19px}.home-hero-title{font-size:2.45rem}.home-hero-panel:after{right:-4%;font-size:13rem}}
/* Premium cast & crew rails */
.people-section{position:relative;margin:2.1rem 0 2.35rem;padding:1.35rem 1.35rem 1.5rem;border:1px solid rgba(255,255,255,.095);border-radius:22px;background:linear-gradient(135deg,rgba(255,255,255,.075),rgba(255,255,255,.018) 48%,rgba(229,9,20,.045));backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);box-shadow:0 18px 55px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.07);overflow:hidden}
.people-section:before{content:"";position:absolute;inset:0 0 auto;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent);pointer-events:none}
.people-heading{display:flex;align-items:end;justify-content:space-between;gap:1rem;margin:0 0 1.2rem}
.people-eyebrow{display:block;color:#ff6b72;font-size:.62rem;font-weight:800;letter-spacing:.2em;margin-bottom:.35rem}
.people-heading h3{font-family:'Oswald',sans-serif;font-size:1.8rem;line-height:1;margin:0;color:#fff;letter-spacing:.015em}
.people-count{color:#8f8f98;font-size:.65rem;letter-spacing:.13em;font-weight:700;white-space:nowrap}
.people-rail{display:flex;gap:1rem;overflow-x:auto;overflow-y:hidden;padding:.25rem .1rem .8rem;scroll-snap-type:x mandatory;scrollbar-width:thin;scrollbar-color:rgba(229,9,20,.65) rgba(255,255,255,.06);-webkit-overflow-scrolling:touch}
.people-rail::-webkit-scrollbar{height:5px}
.people-rail::-webkit-scrollbar-track{background:rgba(255,255,255,.055);border-radius:20px}
.people-rail::-webkit-scrollbar-thumb{background:linear-gradient(90deg,#8f0710,#ed2935);border-radius:20px}
.people-card{position:relative;flex:0 0 154px;min-width:0;padding:1rem .8rem .95rem;text-align:center;border:1px solid rgba(255,255,255,.085);border-radius:17px;background:linear-gradient(155deg,rgba(255,255,255,.105),rgba(255,255,255,.035) 55%,rgba(0,0,0,.16));box-shadow:0 9px 25px rgba(0,0,0,.2),inset 0 1px 0 rgba(255,255,255,.08);scroll-snap-align:start;transition:transform .28s ease,border-color .28s ease,background .28s ease}
.people-card:hover{transform:translateY(-6px);border-color:rgba(255,91,100,.55);background:linear-gradient(155deg,rgba(229,9,20,.16),rgba(255,255,255,.06));box-shadow:0 16px 34px rgba(0,0,0,.36),0 0 24px rgba(229,9,20,.09)}
.people-photo{position:relative;width:112px;height:112px;margin:0 auto .85rem;border-radius:50%;padding:3px;background:linear-gradient(145deg,#ff7b80,#8b1018 48%,rgba(255,255,255,.18));box-shadow:0 7px 24px rgba(0,0,0,.42),0 0 0 5px rgba(255,255,255,.025)}
.people-photo img{display:block;width:100%;height:100%;object-fit:cover;object-position:center 25%;border-radius:50%;border:2px solid #171313}
.people-photo-glow{position:absolute;inset:-5px;border-radius:50%;border:1px solid rgba(255,255,255,.10);pointer-events:none}
.people-avatar-fallback{width:100%;height:100%;display:grid;place-items:center;border-radius:50%;background:radial-gradient(circle at 35% 25%,#4c2528,#171719 70%);color:#ff777e;font-size:2rem}
.people-name{color:#fff;font-size:.9rem;font-weight:750;line-height:1.25;min-height:2.25em;display:flex;align-items:center;justify-content:center}
.people-role{color:#a9a9b2;font-size:.76rem;line-height:1.35;margin-top:.35rem;min-height:2.3em}
@media(max-width:700px){.people-section{padding:1rem .85rem 1.1rem;margin:1.4rem 0 1.7rem;border-radius:17px}.people-heading h3{font-size:1.5rem}.people-count{font-size:.56rem}.people-card{flex-basis:137px;padding:.85rem .65rem}.people-photo{width:96px;height:96px}.people-rail{gap:.75rem}}
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

/* Responsive discovery home */
.home-intro{padding:.25rem 0 .6rem;color:#aaa;font-size:.9rem}
.home-section{margin:1.5rem 0 2rem}
.home-section-head{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:.85rem}
.home-section-title{font-family:'Oswald',sans-serif;font-size:1.35rem;font-weight:600;color:#fff;letter-spacing:.025em}
.home-section-subtitle{color:#888;font-size:.72rem;margin-top:.15rem}
.responsive-movie-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(142px,1fr));gap:14px 12px;align-items:start}
.responsive-movie-card{position:relative;display:block;min-width:0;text-decoration:none!important;color:#fff!important;background:linear-gradient(145deg,rgba(255,255,255,.105),rgba(255,255,255,.025) 58%,rgba(229,9,20,.055));border:1px solid rgba(255,255,255,.11);border-radius:14px;overflow:hidden;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);box-shadow:0 10px 28px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.07);transition:transform .25s ease,border-color .25s ease,box-shadow .25s ease}
.responsive-movie-card:hover{transform:translateY(-6px) scale(1.015);border-color:rgba(255,91,100,.58);box-shadow:0 18px 38px rgba(0,0,0,.48),0 0 25px rgba(229,9,20,.12)}
.responsive-movie-card img{display:block;width:100%;aspect-ratio:2/3;object-fit:cover;background:#202020}
.responsive-movie-card .poster-fallback{aspect-ratio:2/3;display:flex;align-items:center;justify-content:center;background:linear-gradient(145deg,#292929,#101010);font-size:2rem}
.responsive-movie-card .poster-info{padding:10px 11px 12px;background:linear-gradient(180deg,rgba(255,255,255,.025),rgba(0,0,0,.12))}
.responsive-movie-card .poster-title{font-size:.78rem;line-height:1.3;font-weight:700;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.05em}
.responsive-movie-card .poster-rating{font-size:.7rem;color:#f5c518;margin-top:4px}
.home-section-rule{height:1px;background:rgba(255,255,255,.08);margin:1.4rem 0}
@media(min-width:1500px){.responsive-movie-grid{grid-template-columns:repeat(8,minmax(0,1fr));gap:16px}}
@media(min-width:1100px) and (max-width:1499px){.responsive-movie-grid{grid-template-columns:repeat(6,minmax(0,1fr))}}
@media(min-width:769px) and (max-width:1099px){.responsive-movie-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media(min-width:481px) and (max-width:768px){.responsive-movie-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:11px}}
@media(max-width:480px){.responsive-movie-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.home-section-title{font-size:1.18rem}.block-container{padding-left:.8rem;padding-right:.8rem}}
@media(max-width:768px){.cinevault-hero{align-items:flex-start;flex-direction:column}.cinevault-tagline{text-align:left}.hero-panel{padding:1.35rem;min-height:200px}.detail-card{padding:1.1rem}.movie-card:hover,.responsive-movie-card:hover{transform:none}}

@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important}}
/* ── CINEMATIC BACKDROP + OVERLAPPING POSTER + TRAILER POPUP ── */
.movie-hero-overlap{
  position:relative;isolation:isolate;width:100%;min-height:590px;margin:0 0 2.2rem;
  overflow:hidden;border-radius:20px;background:#080808;
}
.movie-hero-backdrop{
  position:absolute;z-index:0;inset:0 0 74px;overflow:hidden;
  background-image:var(--hero-image);background-size:cover;background-position:center 28%;
  border-radius:20px 20px 0 0;
}
.movie-hero-overlap::after{
  content:"";position:absolute;z-index:1;inset:0;pointer-events:none;border-radius:20px;
  background:linear-gradient(180deg,rgba(0,0,0,.16) 0%,rgba(0,0,0,.08) 34%,rgba(0,0,0,.62) 62%,#080808 88%,#080808 100%),
             linear-gradient(90deg,rgba(0,0,0,.16),transparent 72%);
}
.movie-hero-release,.movie-hero-bottom,.movie-hero-play-link{z-index:2}
.movie-hero-release{
  position:absolute;top:24px;right:24px;width:min(330px,36%);padding:15px 18px;border-radius:16px;
  background:rgba(22,22,25,.58);border:1px solid rgba(255,255,255,.18);
  backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);box-shadow:0 12px 35px rgba(0,0,0,.22);color:#fff;
}
.movie-hero-release small{display:block;color:#d0d0d0;font-size:.78rem;margin-bottom:5px}
.movie-hero-release strong{display:block;font-size:1rem}
.movie-hero-release span{display:block;color:#ff795f;font-size:.76rem;margin-top:7px}
.movie-hero-play-link{
  position:absolute;left:50%;top:39%;transform:translate(-50%,-50%);width:76px;height:76px;
  display:flex;align-items:center;justify-content:center;border-radius:50%;
  color:#fff!important;text-decoration:none!important;font-size:1.8rem;line-height:1;
  background:rgba(12,12,14,.58);border:1px solid rgba(255,255,255,.3);
  box-shadow:0 8px 35px rgba(0,0,0,.38);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  transition:transform .2s,background .2s,box-shadow .2s;
}
.movie-hero-play-link:hover{transform:translate(-50%,-50%) scale(1.09);background:rgba(255,75,55,.88);box-shadow:0 12px 40px rgba(255,70,55,.3)}
.movie-hero-bottom{
  position:absolute;left:0;right:0;bottom:0;display:grid;
  grid-template-columns:230px minmax(260px,1fr) minmax(220px,330px);
  gap:28px;align-items:end;padding:0 24px 0 3.5%;
}
.movie-hero-poster{width:100%;aspect-ratio:2/3;object-fit:cover;display:block;border-radius:13px;
  border:1px solid rgba(255,255,255,.17);box-shadow:0 22px 55px rgba(0,0,0,.62)}
.movie-hero-poster-placeholder{aspect-ratio:2/3;border-radius:13px;background:linear-gradient(145deg,#303039,#111);
  display:flex;align-items:center;justify-content:center;font-size:3rem}
.movie-hero-info{padding:0 0 12px;min-width:0}
.movie-hero-kicker{color:#c2c2c2;font-size:.9rem;margin-bottom:5px}
.movie-hero-title{font-size:clamp(1.9rem,3.1vw,3rem);font-weight:800;line-height:1.12;letter-spacing:-.035em;color:#fff;text-shadow:0 4px 24px #000}
.movie-hero-facts{display:flex;flex-wrap:wrap;gap:24px;margin-top:24px}
.movie-hero-fact small{display:block;color:#aaa;font-size:.76rem;margin-bottom:4px}
.movie-hero-fact strong{color:#f3f3f3;font-size:.91rem}
.movie-hero-actions{display:flex;flex-direction:column;gap:10px;padding-bottom:12px}
.movie-hero-actions .action-pill{display:block;text-align:center;padding:13px 16px;border-radius:999px;color:#fff;text-decoration:none;
  font-size:.88rem;font-weight:700;background:rgba(255,255,255,.075);border:1px solid rgba(255,255,255,.15);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
.movie-hero-actions .action-pill.primary{background:linear-gradient(105deg,#ff633d,#c92e49);border-color:rgba(255,255,255,.18);box-shadow:0 8px 25px rgba(218,53,57,.22)}
@media(max-width:850px){
 .movie-hero-overlap{min-height:540px}.movie-hero-backdrop{inset:0 0 65px}
 .movie-hero-bottom{grid-template-columns:170px minmax(190px,1fr);gap:18px;padding:0 18px}
 .movie-hero-actions{grid-column:1/-1;display:flex;padding:0 0 14px}
 .movie-hero-release{top:14px;right:14px;width:min(270px,55%);padding:11px 13px}
 .movie-hero-facts{gap:14px;margin-top:15px}.movie-hero-play-link{top:35%;width:68px;height:68px}
}
@media(max-width:560px){
 .movie-hero-overlap{min-height:610px;margin-top:-.2rem}.movie-hero-backdrop{inset:0 0 225px;background-position:center top}
 .movie-hero-bottom{grid-template-columns:112px minmax(0,1fr);gap:12px;padding:0 12px 12px}
 .movie-hero-info{padding-bottom:8px}.movie-hero-kicker{font-size:.7rem}.movie-hero-title{font-size:1.35rem}
 .movie-hero-facts{gap:9px 14px;margin-top:12px}.movie-hero-fact small{font-size:.64rem}.movie-hero-fact strong{font-size:.74rem}
 .movie-hero-actions{grid-column:1/-1;gap:7px}.movie-hero-actions .action-pill{font-size:.73rem;padding:10px 7px}
 .movie-hero-release{width:58%;top:10px;right:10px}.movie-hero-release small{font-size:.66rem}.movie-hero-release strong{font-size:.82rem}
 .movie-hero-play-link{top:30%;width:60px;height:60px;font-size:1.5rem}
}



.movie-overview-panel{position:relative;margin:26px 0 30px;padding:25px 28px;border:1px solid rgba(255,255,255,.11);border-radius:18px;background:linear-gradient(120deg,rgba(255,255,255,.075),rgba(255,255,255,.025) 60%,rgba(190,35,55,.07));backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);box-shadow:0 14px 38px rgba(0,0,0,.24),inset 0 1px 0 rgba(255,255,255,.06)}
.movie-overview-kicker{font-size:.66rem;letter-spacing:.22em;color:#ed6870;font-weight:800;margin-bottom:7px}
.movie-overview-heading{font-size:1.45rem;font-weight:750;color:#fff;margin-bottom:9px}
.movie-overview-copy{font-size:.96rem;line-height:1.85;color:rgba(245,245,245,.78);max-width:1000px;margin:0}

/* Tickets On - movie-specific ticket platform links */
.ticket-platform-panel{position:relative;margin:26px 0 30px;padding:22px 25px;border:1px solid rgba(255,255,255,.11);border-radius:20px;background:linear-gradient(115deg,rgba(255,255,255,.065),rgba(255,255,255,.018) 58%,rgba(100,65,160,.14));backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);box-shadow:0 14px 38px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.06)}
.ticket-platform-heading{font-size:1.12rem;font-weight:800;color:#f5f5f5;margin:0 0 15px}
.ticket-platform-list{display:flex;flex-direction:column;gap:12px}
.ticket-platform-link{display:flex;align-items:center;gap:13px;min-height:62px;padding:9px 12px;border:1px solid rgba(255,255,255,.075);border-radius:13px;background:rgba(0,0,0,.22);color:#f2f2f2!important;text-decoration:none!important;transition:background .2s,border-color .2s,transform .2s}
.ticket-platform-link:hover{background:rgba(255,255,255,.075);border-color:rgba(255,255,255,.2);transform:translateY(-2px)}
.ticket-platform-logo{width:48px;height:48px;flex:0 0 48px;display:grid;place-items:center;border-radius:11px;color:#fff;font-size:.78rem;font-weight:900;letter-spacing:-.04em;box-shadow:0 5px 16px rgba(0,0,0,.25)}
.ticket-platform-logo.district{background:linear-gradient(145deg,#a82cff,#5a20c9)}
.ticket-platform-logo.bms{background:#e93450;font-size:1rem}
.ticket-platform-copy{min-width:0;flex:1}
.ticket-platform-name{font-size:.98rem;font-weight:800;line-height:1.25}
.ticket-platform-note{font-size:.82rem;color:#aeb0bb;margin-top:4px}
.ticket-platform-arrow{font-size:1.35rem;color:#c9c9d1;padding:0 5px}
@media(max-width:560px){.ticket-platform-panel{padding:18px 15px}.ticket-platform-logo{width:43px;height:43px;flex-basis:43px}.ticket-platform-name{font-size:.9rem}.ticket-platform-note{font-size:.75rem}}

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

@st.dialog("Now Playing", width="large")
def show_trailer_dialog(video_id: str):
    """Open the selected YouTube trailer in a popup dialog."""
    st.video(f"https://www.youtube.com/watch?v={video_id}", autoplay=True)


@st.cache_data(ttl=86400, show_spinner=False)
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
    """Find a matching TMDB poster and verify that it is an actual image."""
    try:
        data, error = api_get_json("/tmdb/search", params={"query": title})
        if error or not isinstance(data, dict):
            return None

        results = data.get("results") or []
        wanted = str(title or "").strip().casefold()
        ordered = sorted(
            results,
            key=lambda movie: (
                str(movie.get("title") or "").strip().casefold() != wanted,
                not bool(movie.get("poster_url") or movie.get("poster_path")),
            ),
        )
        for movie in ordered:
            candidate = clean_image_url(
                movie.get("poster_url") or movie.get("poster_path")
            )
            if candidate and cached_valid_poster_url(candidate):
                return candidate
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


def recover_missing_recommendation_posters(cards):
    """Validate all recommendation images concurrently and recover broken posters."""
    if not cards:
        return cards

    recovered = [dict(card) for card in cards]
    normalized = {
        index: clean_image_url(card.get("poster_url"))
        for index, card in enumerate(recovered)
    }

    # A URL being present does not mean the image exists. Validate all URLs in
    # parallel; cache results for 24 hours to keep subsequent page loads quick.
    with ThreadPoolExecutor(max_workers=10) as pool:
        checks = {
            index: pool.submit(cached_valid_poster_url, url)
            for index, url in normalized.items() if url
        }
        for index, future in checks.items():
            try:
                recovered[index]["poster_url"] = future.result(timeout=15)
            except Exception as exc:
                logger.warning("Poster validation failed for %r: %s",
                               recovered[index].get("title"), exc)
                recovered[index]["poster_url"] = None

    missing = [
        index for index, card in enumerate(recovered)
        if not card.get("poster_url")
    ]

    # Only dead/missing images are searched again. Searches also run concurrently.
    with ThreadPoolExecutor(max_workers=6) as pool:
        lookups = {
            index: pool.submit(
                cached_tmdb_poster_for_title,
                str(recovered[index].get("title") or "")
            )
            for index in missing
        }
        for index, future in lookups.items():
            try:
                recovered[index]["poster_url"] = future.result(timeout=20)
            except Exception as exc:
                logger.warning("Poster recovery failed for %r: %s",
                               recovered[index].get("title"), exc)
                recovered[index]["poster_url"] = None
    return recovered


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
                    # Use a native Streamlit button callback rather than a button
                    # inside an HTML component iframe. This reliably updates the
                    # app's session state and opens the selected movie details.
                    st.button(
                        "▶ View details",
                        key=f"{key_prefix}_details_{tmdb_id}_{r}_{c}_{idx}",
                        on_click=goto_details,
                        args=(tmdb_id,),
                        use_container_width=True,
                    )
                else:
                    st.button(
                        "▶ View details",
                        key=f"{key_prefix}_details_unavailable_{r}_{c}_{idx}",
                        disabled=True,
                        use_container_width=True,
                    )

                st.markdown("</div></div>", unsafe_allow_html=True)



def responsive_poster_section(cards, title, subtitle=None, limit=12):
    """Render a responsive poster grid; CSS auto-adjusts columns to viewport width."""
    if not cards:
        return
    safe_heading = html.escape(str(title))
    subtitle_html = (
        f"<div class='home-section-subtitle'>{html.escape(str(subtitle))}</div>"
        if subtitle else ""
    )
    tiles = []
    for movie in cards[:limit]:
        if not isinstance(movie, dict):
            continue
        movie_id = safe_int(movie.get("tmdb_id") or movie.get("id"))
        if movie_id is None:
            continue
        movie_title = html.escape(str(movie.get("title") or "Untitled"))
        poster_url = clean_image_url(movie.get("poster_url"))
        rating = movie.get("vote_average")
        if poster_url:
            poster_html = (
                f"<img src='{html.escape(poster_url, quote=True)}' "
                f"alt='{movie_title}' loading='lazy'>"
            )
        else:
            poster_html = "<div class='poster-fallback'>🎬</div>"
        rating_html = (
            f"<div class='poster-rating'>★ {html.escape(str(rating))}</div>"
            if rating not in (None, "", "N/A") else ""
        )
        tiles.append(
            f"<a class='responsive-movie-card' href='?view=details&amp;id={movie_id}' target='_self' rel='nofollow'>"
            f"{poster_html}<div class='poster-info'>"
            f"<div class='poster-title'>{movie_title}</div>{rating_html}"
            f"</div></a>"
        )
    if not tiles:
        return
    st.markdown(
        f"<section class='home-section'><div class='home-section-head'>"
        f"<div><div class='home-section-title'>{safe_heading}</div>{subtitle_html}</div>"
        f"</div><div class='responsive-movie-grid'>{''.join(tiles)}</div></section>",
        unsafe_allow_html=True,
    )

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
# Keep the discovery defaults in the main experience (no sidebar navigation).
home_category = "trending"
grid_cols = 6

# CINEMATIC BRAND BAR
st.markdown(
    """
    <div class='cinevault-hero'>
      <a href='/?view=home' style='text-decoration:none;position:relative;z-index:2;'>
        <div class='cinevault-logo'>CINE<span>VAULT</span></div>
      </a>
      <div class='cinevault-tagline'>YOUR NEXT FAVOURITE MOVIE STARTS HERE</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.view == "home":
    st.markdown(
        """
        <section class='home-hero-panel'>
          <div class='home-hero-kicker'>THE CINEMA EXPERIENCE</div>
          <div class='home-hero-title'>Find your next<br><span>great story.</span></div>
          <div class='home-hero-copy'>Discover handpicked favourites, explore what's trending, and find a film that stays with you long after the credits roll.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

# ==========================================================
# ENGINE CORE: VIEW HOME
# ==========================================================
if st.session_state.view == "home":
    st.markdown("<div class='home-search-label'>SEARCH THE VAULT</div><div class='home-search-row'>", unsafe_allow_html=True)
    typed = st.text_input(
        "Search movies",
        placeholder="Search a title, actor, or a world you want to explore…",
        label_visibility="collapsed",
        key="cinevault_home_search",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='home-section-rule'></div>", unsafe_allow_html=True)

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

    # ── MULTI-SECTION HOME DISCOVERY ──
    home_sections = [
        ("Top All Time", "top_rated", "Audience favourites across the years"),
        ("Trending Now", "trending", "What people are watching right now"),
        ("Popular Movies", "popular", "Popular picks from the movie vault"),
        ("Now Playing", "now_playing", "Movies currently in theatres"),
        ("Coming Soon", "upcoming", "Upcoming releases to look forward to"),
    ]

    for section_title, section_category, section_subtitle in home_sections:
        with st.spinner(f"Loading {section_title.lower()}…"):
            section_data, section_error = api_get_json(
                "/home/paged",
                params={"category": section_category, "page": 1, "limit": 12},
            )
        if section_error:
            st.caption(f"{section_title} is temporarily unavailable.")
            logger.warning("Home section %s failed: %s", section_category, section_error)
            continue
        # The deployed /home/paged endpoint returns a plain JSON list.
        # normalize_recommendations supports both list and wrapped-object formats.
        section_cards = normalize_recommendations(section_data)
        responsive_poster_section(
            section_cards,
            section_title,
            section_subtitle,
            limit=12,
        )

    st.markdown("<div class='home-section-rule'></div>", unsafe_allow_html=True)
    browse_label = home_category.replace("_", " ").title()
    st.markdown(
        f"<div class='section-label'>Browse All · {html.escape(browse_label)}</div>",
        unsafe_allow_html=True,
    )

    if "home_page" not in st.session_state:
        st.session_state.home_page = 1
    if "last_home_category" not in st.session_state:
        st.session_state.last_home_category = home_category
    if st.session_state.last_home_category != home_category:
        st.session_state.home_page = 1
        st.session_state.last_home_category = home_category

    page_size = 20  # TMDB's standard page size used by the deployed backend.
    with st.spinner("Loading more movies…"):
        home_data, err = api_get_json(
            "/home/paged",
            params={"category": home_category, "page": st.session_state.home_page, "limit": page_size},
        )

    if err:
        st.error(f"Home feed failed: {err}")
        st.stop()

    # The current FastAPI /home/paged endpoint returns a plain JSON list,
    # rather than {"results": [...], "total_pages": ...}.
    home_cards = normalize_recommendations(home_data)
    if not home_cards:
        st.info("No movies are available in this category right now. Please choose another category.")
        st.stop()

    # The list response has no pagination metadata. A full page indicates
    # that another page may exist; a shorter page is the final page.
    has_next_page = len(home_cards) >= page_size
    st.caption(f"Page {st.session_state.home_page} · {len(home_cards)} movies")
    responsive_poster_section(
        home_cards,
        f"{browse_label} · Page {st.session_state.home_page}",
        "Continue exploring the full catalogue",
        limit=page_size,
    )

    prev_col, page_col, next_col = st.columns([1, 2, 1])
    with prev_col:
        if st.button("← Previous", disabled=st.session_state.home_page <= 1, key="home_previous"):
            st.session_state.home_page -= 1
            st.rerun()
    with page_col:
        st.markdown(
            f"<div style='text-align:center;padding:.55rem 0;'>Page {st.session_state.home_page}</div>",
            unsafe_allow_html=True,
        )
    with next_col:
        if st.button("Next →", disabled=not has_next_page, key="home_next"):
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

    # ── FETCH TRAILER BEFORE BUILDING THE HERO ──
    title = (data.get("title") or "").strip()
    with st.spinner("Finding the official trailer..."):
        video_id = cached_trailer_id(title) if title else None

    # ── OVERLAPPING CINEMATIC HERO WITH POSTER + CLICK-TO-PLAY TRAILER POPUP ──
    backdrop_url = clean_image_url(data.get("backdrop_url"))
    poster_url = clean_image_url(data.get("poster_url"))
    safe_detail_title = html.escape(str(data.get("title") or "Untitled"))
    release_date = str(data.get("release_date") or "")
    release_year = release_date[:4] if release_date else "Movie"
    genres = [
        str(g.get("name", "")) for g in (data.get("genres") or [])
        if isinstance(g, dict) and g.get("name")
    ]
    rating = data.get("vote_average")
    genre_text = " · ".join(genres[:3]) if genres else "Movie"
    rating_text = f"★ {html.escape(str(rating))}" if rating not in (None, "") else ""
    safe_backdrop = html.escape(backdrop_url or "", quote=True)
    bg_style = (
        f"--hero-image:url('{safe_backdrop}');" if safe_backdrop
        else "--hero-image:linear-gradient(135deg,#303039,#080808);"
    )
    poster_markup = (
        f"<img class='movie-hero-poster' src='{html.escape(poster_url, quote=True)}' alt='{safe_detail_title} poster'>"
        if poster_url else "<div class='movie-hero-poster-placeholder'>🎬</div>"
    )
    release_markup = ""
    if release_date:
        release_markup = (
            "<div class='movie-hero-release'>"
            "<small>Release Date</small>"
            f"<strong>{html.escape(release_date)}</strong>"
            f"<span>{rating_text or 'CineVault movie details'}</span>"
            "</div>"
        )

    # Clicking this play control sets a one-time query flag; Streamlit reruns,
    # consumes the flag, and opens the native dialog with the trailer autoplaying.
    trailer_link = ""
    if video_id:
        current_id = int(tmdb_id)
        trailer_link = (
            f"<a class='movie-hero-play-link' aria-label='Play trailer' title='Play trailer' "
            f"href='?view=details&amp;id={current_id}&amp;play_trailer=1'>▶</a>"
        )

    st.markdown(
        f"""
        <section class="movie-hero-overlap" style="{bg_style}">
          <div class="movie-hero-backdrop"></div>
          {release_markup}
          {trailer_link}
          <div class="movie-hero-bottom">
            <div>{poster_markup}</div>
            <div class="movie-hero-info">
              <div class="movie-hero-kicker">Movie &nbsp;•&nbsp; {html.escape(release_year)} &nbsp;•&nbsp; {html.escape(genre_text)}</div>
              <div class="movie-hero-title">{safe_detail_title}</div>
              <div class="movie-hero-facts">
                <div class="movie-hero-fact"><small>Rating</small><strong>{rating_text or 'Not rated'}</strong></div>
                <div class="movie-hero-fact"><small>Genres</small><strong>{html.escape(', '.join(genres[:2]) or 'Not available')}</strong></div>
              </div>
            </div>
            <div class="movie-hero-actions">
              <div class="action-pill primary">{'▶  Play Official Trailer' if video_id else 'Trailer unavailable'}</div>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # Consume the play request once, then launch the YouTube player in a popup.
    play_trailer_requested = st.query_params.get("play_trailer") == "1"
    if play_trailer_requested:
        if "play_trailer" in st.query_params:
            del st.query_params["play_trailer"]
        if video_id:
            show_trailer_dialog(str(video_id))
        else:
            st.info("No YouTube trailer was found for this movie.")

    if not video_id:
        st.caption("No YouTube trailer was found for this movie. The movie backdrop and poster are shown instead.")

    # Movie overview appears below the overlapping trailer hero.
    overview_text = str(data.get("overview") or "").strip()
    if not overview_text:
        overview_text = str(data.get("tagline") or "").strip()
    if not overview_text:
        overview_text = "A synopsis for this film is not available yet. Explore its cast, crew and recommendations below."
    overview = html.escape(overview_text)
    st.markdown(
        f"<section class='movie-overview-panel'>"
        f"<div class='movie-overview-kicker'>THE STORY</div>"
        f"<div class='movie-overview-heading'>Overview</div>"
        f"<p class='movie-overview-copy'>{overview}</p>"
        f"</section>",
        unsafe_allow_html=True,
    )

    # ── TICKETS ON: open the selected movie on ticket platforms ──
    ticket_movie_query = quote_plus(title)
    district_url = f"https://www.district.in/movies?query={ticket_movie_query}"
    bookmyshow_url = f"https://in.bookmyshow.com/explore/movies?query={ticket_movie_query}"
    safe_ticket_title = html.escape(title or "this movie")

    st.markdown(
        f"""
        <section class="ticket-platform-panel">
          <div class="ticket-platform-heading">Tickets On</div>
          <div class="ticket-platform-list">
            <a class="ticket-platform-link" href="{district_url}" target="_blank" rel="noopener noreferrer">
              <span class="ticket-platform-logo district">district</span>
              <span class="ticket-platform-copy">
                <span class="ticket-platform-name">District</span>
                <span class="ticket-platform-note">Find {safe_ticket_title} showtimes and tickets</span>
              </span>
              <span class="ticket-platform-arrow">↗</span>
            </a>
            <a class="ticket-platform-link" href="{bookmyshow_url}" target="_blank" rel="noopener noreferrer">
              <span class="ticket-platform-logo bms">my</span>
              <span class="ticket-platform-copy">
                <span class="ticket-platform-name">BookMyShow</span>
                <span class="ticket-platform-note">Find {safe_ticket_title} showtimes and tickets</span>
              </span>
              <span class="ticket-platform-arrow">↗</span>
            </a>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # ── CAST & CREW: premium horizontal glass carousels ──
    def render_people_rail(section_title, people, role_key, fallback_role, limit):
        valid_people = [person for person in (people or [])[:limit] if isinstance(person, dict)]
        if not valid_people:
            return
        cards = [f"<section class='people-section'><div class='people-heading'><div><span class='people-eyebrow'>THE PEOPLE BEHIND THE FILM</span><h3>{section_title}</h3></div><span class='people-count'>{len(valid_people):02d} MEMBERS</span></div><div class='people-rail'>"]
        for person in valid_people:
            person_name = html.escape(str(person.get("name") or "Unknown"))
            role = html.escape(str(person.get(role_key) or fallback_role))
            image_url = clean_image_url(person.get("profile_url"))
            if image_url:
                portrait = f"<img src='{html.escape(image_url, quote=True)}' alt='{person_name}' loading='lazy'>"
            else:
                portrait = "<div class='people-avatar-fallback'>✦</div>"
            cards.append(
                "<article class='people-card'>"
                f"<div class='people-photo'>{portrait}<span class='people-photo-glow'></span></div>"
                f"<div class='people-name'>{person_name}</div>"
                f"<div class='people-role'>{role}</div>"
                "</article>"
            )
        cards.append("</div></section>")
        st.markdown("".join(cards), unsafe_allow_html=True)

    render_people_rail("Cast", data.get("cast"), "character", "Cast", 12)
    render_people_rail("Crew", data.get("crew"), "job", "Crew", 8)

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

            similar_cards = recover_missing_recommendation_posters(normalize_recommendations(tfidf_items))

            if similar_cards:
                responsive_poster_section(
                    similar_cards,
                    "Similar Films",
                    subtitle="Because you enjoyed this movie",
                    limit=12,
                )
            else:
                st.warning("No similar films were returned by the recommendation engine.")

            genre_cards = recover_missing_recommendation_posters(normalize_recommendations(genre_items))

            if genre_cards:
                responsive_poster_section(
                    genre_cards,
                    "More Like This",
                    subtitle="Explore more from the same genres",
                    limit=12,
                )
            else:
                st.info("No genre recommendations found.")

        else:
            st.warning("Unexpected recommendation API response.")

    else:
        st.warning("No title available to compute recommendations.")