import streamlit as st
import altair as alt

from utils import (
    inject_pastel_theme_css,
    render_shimmer_loader_css,
    fetch_news,   # ✅ correct
    extract_keywords,
    buzz_meter_value,
)



st.set_page_config(page_title="AI Trends", page_icon="📈", layout="wide")
inject_pastel_theme_css()
render_shimmer_loader_css()


st.markdown("### Trends")
st.caption("Top keywords and today's buzz intensity.")

query = st.text_input("Topic", value="Artificial Intelligence")
source_choice = st.selectbox("Source", ["Google News RSS", "NewsAPI (requires key in secrets)"])
max_items = st.slider("Max articles", 5, 40, 20)

with st.spinner("Fetching news for trends..."):
    articles = fetch_news(query=query, days=7, max_items=max_items)  


texts = [ (a.get("title") or "") + ". " + (a.get("summary") or "") for a in articles ]
kw = extract_keywords(texts, top_k=10)

if not kw:
    st.markdown("<div class='warning-card'>No data to analyze.</div>", unsafe_allow_html=True)
else:
    data = [{"keyword": k, "count": c} for k, c in kw]
    chart = (
        alt.Chart(alt.Data(values=data))
        .mark_bar(color="#a3c4f3")
        .encode(x=alt.X("count:Q", title="Frequency"), y=alt.Y("keyword:N", sort='-x', title="Keyword"))
        .properties(height=360)
    )
    st.altair_chart(chart, use_container_width=True)

col1, col2 = st.columns([0.5, 0.5])
with col1:
    st.markdown("#### Buzz Meter")
    val = buzz_meter_value(articles)
    st.progress(val, text=f"{val}%")

with col2:
    st.markdown("#### Notes")
    st.write("Buzz reflects volume only, not quality of coverage.")


