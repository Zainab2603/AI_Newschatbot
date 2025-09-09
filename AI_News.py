import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from pathlib import Path

from utils import (
    inject_pastel_theme_css,
    fetch_news,  # new signature with days
    render_shimmer_loader_css,
    summarize_text,
    analyze_sentiment_batch,
    get_daily_streak,
    increment_daily_streak,
    ensure_data_dir,
    tts_generate_mp3,
)


st.set_page_config(
    page_title="AI News • Pastel",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_pastel_theme_css()
render_shimmer_loader_css()
ensure_data_dir()


def render_header():
    with st.container():
        st.markdown(
            """
            <div class="pastel-header">
                <div class="title">AI News</div>
                <div class="subtitle">Curated updates, trends, and insights.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_sidebar():
    with st.sidebar:
        st.markdown("### Filters")
        st.caption("Adjust your feed preferences.")
        default_query = st.text_input("🔍 Search news:", value="AI")
        source_choice = st.selectbox(
            "Source",
            ["Google News RSS", "NewsAPI (requires key in secrets)"]
        )
        max_items = st.slider("Max articles", min_value=5, max_value=40, value=15)
        days = st.slider("Days back", min_value=1, max_value=14, value=7)

        st.markdown("---")
        # Streak
        streak = get_daily_streak()
        st.markdown(
            f"<div class='streak-chip'>🔥 {streak} day streak</div>", unsafe_allow_html=True
        )

        # Prediction quick access
        st.markdown("---")
        st.markdown("### Prediction Challenge")
        st.caption("Will AI trend increase tomorrow?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Yes 👍", key="pred_yes"):
                st.session_state["prediction_vote"] = "yes"
                st.success("Voted Yes")
        with col_no:
            if st.button("No 👎", key="pred_no"):
                st.session_state["prediction_vote"] = "no"
                st.success("Voted No")

        return default_query, source_choice, max_items, days


def render_article_card(article, index: int):
    title = article.get("title") or "Untitled"
    summary = summarize_text(article.get("summary") or article.get("description") or "")
    url = article.get("link") or article.get("url") or ""
    source = article.get("source") or article.get("source_name") or "Unknown"
    published = article.get("published") or article.get("publishedAt") or ""
    date_str = ""
    if published:
        try:
            date_parsed = (
                datetime.fromisoformat(published.replace("Z", "+00:00"))
                if "T" in published else datetime.strptime(published[:25], "%a, %d %b %Y %H:%M:%S")
            )
            date_str = date_parsed.strftime("%b %d, %Y")
        except Exception:
            date_str = published

    st.markdown(
        f"""
        <div class="news-card" id="card-{index}">
            <h2 class="headline">{title}</h2>
            <p class="summary">{summary}</p>
            <div class="meta">{source} • {date_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([0.15, 0.35, 0.5])
    with c1:
        if st.button("Read More", key=f"read_{index}"):
            st.markdown(f"[Open Article]({url})")
    with c2:
        tone = st.selectbox("Voice tone", ["🎩 Formal", "😎 Casual", "🤨 Sarcastic"], key=f"tone_{index}")
        if st.button("Play News 🎙️", key=f"listen_{index}"):
            preface = {
                "🎩 Formal": "Here is a formal reading of the news.",
                "😎 Casual": "Here's the news in a casual tone.",
                "🤨 Sarcastic": "Alright, here's your 'amazing' news...",
            }.get(tone, "Here is the news.")
            mp3_path = tts_generate_mp3(f"{preface} {title}. {summary}")
            if mp3_path:
                st.audio(str(mp3_path))
            else:
                st.warning("TTS unavailable. Please install gTTS.")
    with c3:
        st.progress(0, text="Sentiment")


def main():
    render_header()
    # Top search and refresh controls
    top_col1, top_col2, top_col3 = st.columns([0.6, 0.2, 0.2])
    with top_col1:
        top_query = st.text_input("🔍 Search news", value=st.session_state.get("top_query", "AI"), key="top_query")
    with top_col2:
        if st.button("Refresh 🔄"):
            st.rerun()
    with top_col3:
        auto = st.checkbox("Auto-refresh 60s", value=False)
        if auto:
            try:
                st.autorefresh(interval=60_000, key="auto_refresh")  # Streamlit >=1.36
            except Exception:
                components.html("""
                    <script>
                      setTimeout(function(){ window.location.reload(); }, 60000);
                    </script>
                """, height=0, width=0)

    query, source_choice, max_items, days = render_sidebar()

    with st.container():
        with st.spinner("Fetching the latest AI news..."):
            st.markdown(
                """
                <div class="shimmer shimmer-block"></div>
                """,
                unsafe_allow_html=True,
            )
            # Prefer top search value if provided
            effective_query = (top_query or "").strip() or "AI"
            # Support new helper as requested
            articles = fetch_news(query=effective_query, days=days, max_items=max_items)


    if not articles:
        st.markdown(
            """
            <div class="warning-card">No articles available. Try a different query or source.</div>
            """,
            unsafe_allow_html=True,
        )
        return

    sentiments = analyze_sentiment_batch([
        (a.get("title") or "") + ". " + (a.get("summary") or a.get("description") or "")
        for a in articles
    ])

    # Display cards with subtle entrance animation order
    for idx, (article, senti) in enumerate(zip(articles, sentiments)):
        render_article_card(article, idx)
        # Replace placeholder progress with actual score visualization
        score = senti.get("compound", 0.0)
        label = senti.get("label", "neutral").capitalize()
        st.progress(int((score + 1) * 50), text=f"Sentiment: {label}")
        st.markdown("<div class='fade-in-sep'></div>", unsafe_allow_html=True)

    # Update streak at the end of a successful visit
    increment_daily_streak()


if __name__ == "__main__":
    main()


