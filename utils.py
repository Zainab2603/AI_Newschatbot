from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import streamlit as st


# Optional imports guarded to avoid hard failures
try:
    import feedparser  # type: ignore
except Exception:  # pragma: no cover
    feedparser = None

try:
    from nltk.sentiment import SentimentIntensityAnalyzer  # type: ignore
    import nltk  # type: ignore
except Exception:  # pragma: no cover
    SentimentIntensityAnalyzer = None
    nltk = None

try:
    from sklearn.feature_extraction.text import CountVectorizer
except Exception:  # pragma: no cover
    CountVectorizer = None

try:
    from gtts import gTTS  # type: ignore
except Exception:  # pragma: no cover
    gTTS = None

DATA_DIR = Path(".ai_news_data")


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def inject_pastel_theme_css():
    st.markdown(
        """
        <style>
        /* Main background */
        .stApp {
            background-color: #ffeef5 !important; /* Soft pastel pink */
            color: #333333;
            font-family: "Segoe UI", "Helvetica Neue", sans-serif;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #f8f1f5 !important; /* light pink tint */
        }

        /* Buttons */
        div.stButton > button {
            background-color: #d6f3fb !important; /* Baby blue */
            color: #000 !important;
            border-radius: 12px !important;
            border: none !important;
            font-weight: 500 !important;
            padding: 0.6rem 1.2rem !important;
            transition: background-color 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #c0e9f7 !important; /* Slightly darker baby blue */
            color: white !important;
        }

        /* Selectbox / dropdown */
        div[data-baseweb="select"] > div {
            background-color: #d6f3fb !important; /* Baby blue */
            border-radius: 8px !important;
        }

        /* Sliders */
        .stSlider [role="slider"] {
            background-color: #b3e0f2 !important; /* Baby blue handle */
        }
        .stSlider .st-bo {
            background: linear-gradient(to right, #87CEEB, #ADD8E6) !important;
        }

        /* Text inputs */
        input[type="text"], textarea {
            background-color: #ffffff !important;
            border: 1px solid #ADD8E6 !important;
            border-radius: 8px !important;
            padding: 0.4rem 0.6rem !important;
        }

        /* Cards (like news items) */
        .stMarkdown div {
            border-radius: 16px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def render_shimmer_loader_css() -> None:
    st.markdown(
        """
        <style>
        .shimmer {
            position: relative; overflow: hidden; background: #eef2ff; border-radius: 14px; height: 14px;
        }
        .shimmer-block { height: 60px; margin: 6px 0 18px 0; }
        .shimmer::after {
            content: ""; position: absolute; top:0; left:-150px; height: 100%; width: 150px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent);
            animation: shimmer 1.2s infinite;
        }
        @keyframes shimmer { 100% { transform: translateX(300%); } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_flip_card_css():
    st.markdown(
        """
        <style>
        .card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-top: 1rem;
        }
        .flip-card {
            perspective: 1000px;
        }
        .flip-toggle {
            display: none;
        }
        .flip-inner {
            position: relative;
            width: 100%;
            height: 180px;
            text-align: center;
            transition: transform 0.8s;
            transform-style: preserve-3d;
            cursor: pointer;
        }
        .flip-toggle:checked + label .flip-inner {
            transform: rotateY(180deg);
        }
        .flip-front, .flip-back {
            position: absolute;
            width: 100%;
            height: 100%;
            backface-visibility: hidden;
            border-radius: 16px;
            padding: 1rem;
            font-size: 1rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            background: #E6E6FA; /* Soft lavender */
            color: #333;
        }
        .flip-back {
            transform: rotateY(180deg);
        }
        .flip-hint {
            text-align: center;
            font-size: 0.8rem;
            margin-top: 0.3rem;
            color: #888;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )






def _init_vader() -> Optional[SentimentIntensityAnalyzer]:
    if SentimentIntensityAnalyzer is None:
        return None
    try:
        # Ensure lexicon is present
        import nltk  # type: ignore
        nltk.download('vader_lexicon', quiet=True)
        return SentimentIntensityAnalyzer()
    except Exception:
        return None


def analyze_sentiment_batch(texts: List[str]) -> List[Dict[str, float | str]]:
    sia = _init_vader()
    results: List[Dict[str, float | str]] = []
    for t in texts:
        if not sia:
            results.append({"compound": 0.0, "label": "neutral"})
            continue
        scores = sia.polarity_scores(t or "")
        label = "positive" if scores["compound"] > 0.2 else ("negative" if scores["compound"] < -0.2 else "neutral")
        scores["label"] = label
        results.append(scores)  # type: ignore[arg-type]
    return results




def summarize_text(text: str, max_chars: int = 220) -> str:
    if not text:
        return ""
    t = text.strip().replace("\n", " ")
    if len(t) <= max_chars:
        return t
    # try cut on sentence boundary
    stop = max(t.rfind(". ", 0, max_chars), t.rfind("; ", 0, max_chars), t.rfind(", ", 0, max_chars))
    if stop < 40:
        stop = max_chars
    return t[:stop].rstrip() + "…"


def extract_keywords(texts: List[str], top_k: int = 10) -> List[Tuple[str, int]]:
    if not texts:
        return []
    if CountVectorizer is None:
        # naive fallback
        tokens: List[str] = []
        fillers = set(["the","from","says","and","or","a","an","to","in","of","on","for","with"])
        for t in texts:
            for w in (t or "").lower().split():
                w = ''.join(ch for ch in w if ch.isalnum())
                if len(w) < 3 or w in fillers:
                    continue
                tokens.append(w)
        cnt = Counter(tokens)
        return cnt.most_common(top_k)

    vect = CountVectorizer(stop_words="english", ngram_range=(1, 2), max_features=3000)
    X = vect.fit_transform(texts)
    sums = X.sum(axis=0)
    freq = [(word, int(sums[0, idx])) for word, idx in vect.vocabulary_.items()]
    freq.sort(key=lambda x: x[1], reverse=True)
    return freq[:top_k]


def buzz_meter_value(articles: List[Dict]) -> int:
    # Simple proxy: number of articles normalized to 0-100 scale
    n = len(articles)
    return max(5, min(100, int(100 * (n / 40))))


def tts_generate_mp3(text: str) -> Optional[Path]:
    if not gTTS:
        return None
    try:
        ensure_data_dir()
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        out = DATA_DIR / f"tts_{ts}.mp3"
        gTTS(text=text, lang='en').save(str(out))
        return out
    except Exception:
        return None


# Streak persistence
STREAK_FILE = DATA_DIR / "streak.json"


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _save_json(path: Path, data: Dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')


def get_daily_streak() -> int:
    ensure_data_dir()
    data = _load_json(STREAK_FILE)
    return int(data.get("streak", 0))


def increment_daily_streak() -> None:
    ensure_data_dir()
    data = _load_json(STREAK_FILE)
    last = data.get("last_date")
    today = datetime.now().strftime("%Y-%m-%d")
    if last == today:
        # already counted
        return
    streak = int(data.get("streak", 0))
    # naive: if visited yesterday, continue, else reset
    try:
        from datetime import timedelta
        yday = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        if last == yday:
            streak += 1
        else:
            streak = 1
    except Exception:
        streak = 1
    data.update({"streak": streak, "last_date": today})
    _save_json(STREAK_FILE, data)


# Simple location heuristics for News Map
KNOWN_PLACES = {
    "San Francisco": (37.7749, -122.4194),
    "New York": (40.7128, -74.0060),
    "London": (51.5074, -0.1278),
    "Paris": (48.8566, 2.3522),
    "Berlin": (52.5200, 13.4050),
    "Tokyo": (35.6895, 139.6917),
    "Beijing": (39.9042, 116.4074),
    "Seoul": (37.5665, 126.9780),
    "Bengaluru": (12.9716, 77.5946),
    "Mumbai": (19.0760, 72.8777),
    "Sydney": ( -33.8688, 151.2093),
    "Toronto": (43.6532, -79.3832),
}


def guess_location_from_text(text: str) -> Optional[Tuple[float, float, str]]:
    if not text:
        return None
    for name, (lat, lon) in KNOWN_PLACES.items():
        if name.lower() in text.lower():
            return lat, lon, name
    return None


# New: fetch_news(query, days) helper for Google News RSS
@st.cache_data(ttl=60)
def fetch_news(query: str = "AI", days: int = 7, max_items: int = 40) -> List[Dict]:
    if not feedparser:
        return []
    q = query.replace(" ", "+")
    rss_url = f"https://news.google.com/rss/search?q={q}+when:{days}d&hl=en-US&gl=US&ceid=US:en"
    articles: List[Dict] = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:max_items]:
            articles.append({
                "title": entry.get("title"),
                "summary": entry.get("summary"),
                "link": entry.get("link"),
                "published": entry.get("published"),
                "source": getattr(entry, "source", {}).get("title") if hasattr(entry, "source") else "Google News",
            })
    except Exception:
        return []
    return articles


# Geocoding with geopy Nominatim
def geocode_locations_for_articles(articles: List[Dict], sentiments: List[Dict]) -> List[Tuple[float, float, str, str, str]]:
    try:
        from geopy.geocoders import Nominatim  # type: ignore
    except Exception:
        # fallback to heuristic known places only
        points: List[Tuple[float, float, str, str, str]] = []
        for a, s in zip(articles, sentiments):
            text = (a.get("title") or "") + " " + (a.get("summary") or "")
            gl = guess_location_from_text(text)
            if not gl:
                continue
            lat, lon, name = gl
            emo = "😊" if s.get("label") == "positive" else ("😐" if s.get("label") == "neutral" else "☹️")
            points.append((lat, lon, name, a.get("title") or "Untitled", emo))
        return points

    geolocator = Nominatim(user_agent="ai_news_app")
    points: List[Tuple[float, float, str, str, str]] = []
    for a, s in zip(articles, sentiments):
        title = a.get("title") or ""
        summary = a.get("summary") or ""
        candidates = []
        for token in (title + " " + summary).split():
            clean = ''.join(ch for ch in token if ch.isalnum() or ch in [',','-'])
            if clean and clean[0].isupper() and len(clean) >= 3:
                candidates.append(clean)
        text_query = " ".join(candidates[:8]) or title
        try:
            loc = geolocator.geocode(text_query, timeout=5)
        except Exception:
            loc = None
        if not loc:
            # try heuristic fallback
            gl = guess_location_from_text(title + " " + summary)
            if not gl:
                continue
            lat, lon, name = gl
        else:
            lat, lon = loc.latitude, loc.longitude
            name = loc.address.split(',')[0] if loc and loc.address else text_query
        emo = "😊" if s.get("label") == "positive" else ("😐" if s.get("label") == "neutral" else "☹️")
        points.append((lat, lon, name, title or "Untitled", emo))
    return points


# Buzzword dataset
BUZZWORDS: Dict[str, List[Dict[str, str]]] = {
    "Easy": [
        {"term": "AI", "definition": "Artificial Intelligence: systems designed to perform tasks that typically require human intelligence.", "fun_fact": "The term 'Artificial Intelligence' was coined in 1956 at the Dartmouth Conference."},
        {"term": "Chatbot", "definition": "A computer program that simulates conversation with users.", "fun_fact": "ELIZA, one of the first chatbots, was built in 1966."},
        {"term": "Machine Learning", "definition": "A type of AI where systems learn patterns from data instead of being explicitly programmed.", "fun_fact": "Netflix uses ML to recommend shows based on your watch history."}
    ],
    "Medium": [
        {"term": "Neural Network", "definition": "A system of algorithms designed to recognize patterns by mimicking how the human brain works.", "fun_fact": "Deep neural networks power image recognition in self-driving cars."},
        {"term": "Prompt Engineering", "definition": "The practice of crafting effective inputs (prompts) to guide AI models’ outputs.", "fun_fact": "Good prompt engineering can drastically improve AI performance without changing the model."},
        {"term": "Generative AI", "definition": "AI that can create new content, like text, images, or music, based on learned patterns.", "fun_fact": "DALL·E, from OpenAI, can generate original art from text prompts."}
    ],
    "Expert": [
        {"term": "LLM", "definition": "Large Language Model: a type of AI trained on massive text datasets to generate human-like text.", "fun_fact": "GPT-4 reportedly has hundreds of billions of parameters."},
        {"term": "Reinforcement Learning", "definition": "An AI training method where agents learn by trial and error, receiving rewards or penalties.", "fun_fact": "DeepMind’s AlphaGo used reinforcement learning to defeat human Go champions."},
        {"term": "Transformers", "definition": "A deep learning architecture that powers most modern LLMs by using attention mechanisms.", "fun_fact": "The 2017 paper *Attention is All You Need* introduced Transformers, revolutionizing AI."}
    ]
}

import time
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
import requests
import streamlit as st

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

def _google_news_url(query: str, days_back: int, region="US", lang="en") -> str:
    q = quote_plus(query.strip()) if query else "AI"
    days = max(1, int(days_back or 7))
    return (
        f"https://news.google.com/rss/search?"
        f"q={q}+when:{days}d&hl={lang}-{region}&gl={region}&ceid={region}:{lang}"
    )

@st.cache_data(ttl=300, show_spinner=False)
def fetch_google_news(query: str = "AI",
                      days_back: int = 7,
                      max_articles: int = 15,
                      region: str = "US",
                      lang: str = "en") -> tuple[list[dict], str | None]:
    """
    Returns (articles, error). Articles is a list of dicts with title, link, published, source.
    Cached 5 minutes.
    """
    url = _google_news_url(query, days_back, region, lang)

    # --- HTTP with retries & UA ---
    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": _UA}, timeout=10)
            r.raise_for_status()
            xml_text = r.text
            break
        except Exception as e:
            last_err = e
            time.sleep(0.5 * (attempt + 1))
    else:
        return [], f"HTTP error fetching RSS: {last_err}"

    # --- Parse RSS (XML first, feedparser fallback) ---
    articles: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pubdate = (item.findtext("pubDate") or "").strip()

            # Google News puts source in a namespaced element sometimes
            source = ""
            for child in list(item):
                if "source" in child.tag.lower():
                    source = (child.text or "").strip()
                    break

            if title and link:
                articles.append({
                    "title": title,
                    "link": link,
                    "published": pubdate,
                    "source": source
                })
            if len(articles) >= max(1, int(max_articles or 15)):
                break

    except Exception:
        # Fallback to feedparser if XML path fails
        try:
            import feedparser
            feed = feedparser.parse(xml_text)
            for e in feed.entries[:max(1, int(max_articles or 15))]:
                title = getattr(e, "title", "").strip()
                link = getattr(e, "link", "").strip()
                pubdate = getattr(e, "published", "").strip()
                source = ""
                # feedparser sometimes exposes source as a dict-like
                if hasattr(e, "source") and hasattr(e.source, "title"):
                    source = (e.source.title or "").strip()
                if title and link:
                    articles.append({
                        "title": title,
                        "link": link,
                        "published": pubdate,
                        "source": source
                    })
        except Exception as e2:
            return [], f"Parse error: {e2}"

    if not articles:
        return [], "Feed returned no items (query/source may be blocked or empty)."

    return articles, None

def fetch_news(query: str = "AI", days: int = 7, max_items: int = 40) -> list[dict]:
    articles, err = fetch_google_news(query=query, days_back=days, max_articles=max_items)
    if err:
        st.warning(err)
    return articles
