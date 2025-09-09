import streamlit as st
from utils import inject_pastel_theme_css, render_shimmer_loader_css, fetch_news, analyze_sentiment_batch


st.set_page_config(page_title="Bias & Sentiment", page_icon="🧭", layout="wide")
inject_pastel_theme_css()
render_shimmer_loader_css()

st.markdown("### Bias & Sentiment Analysis")
st.caption("Lightweight sentiment over recent articles.")

query = st.text_input("Topic", value="Artificial Intelligence")
source_choice = st.selectbox("Source", ["Google News RSS", "NewsAPI (requires key in secrets)"])
max_items = st.slider("Max articles", 5, 40, 15)

with st.spinner("Fetching and analyzing..."):
    articles = fetch_news(query=query, days=7, max_items=max_items)
    texts = [ (a.get("title") or "") + ". " + (a.get("summary") or "") for a in articles ]
    scores = analyze_sentiment_batch(texts)

if not articles:
    st.markdown("<div class='warning-card'>No articles for analysis.</div>", unsafe_allow_html=True)
else:
    pos = sum(1 for s in scores if s.get("label") == "positive")
    neg = sum(1 for s in scores if s.get("label") == "negative")
    neu = len(scores) - pos - neg

    st.markdown("#### Distribution")
    st.progress(int(100 * pos / len(scores)), text=f"Positive {pos}")
    st.progress(int(100 * neu / len(scores)), text=f"Neutral {neu}")
    st.progress(int(100 * neg / len(scores)), text=f"Negative {neg}")

    st.markdown("---")
    st.markdown("#### Samples")
    for a, s in zip(articles[:6], scores[:6]):
        st.markdown(f"**{a.get('title','Untitled')}**")
        st.caption(f"Sentiment: {s.get('label','neutral').capitalize()} (compound {s.get('compound',0):.2f})")


