import streamlit as st
from utils import inject_pastel_theme_css, fetch_news



st.set_page_config(page_title="Insights", page_icon="🧠", layout="wide")
inject_pastel_theme_css()

st.markdown("### Insights")
st.caption("Summarized trends powered by Llama 3.2 (via Ollama).")

query = st.text_input("Topic", value="Artificial Intelligence")

max_items = st.slider("Max articles", 5, 40, 15)

articles = fetch_news(query=query, days=7, max_items=max_items)
titles = [a.get("title") or "" for a in articles]

try:
    import ollama  # type: ignore
except Exception:
    ollama = None

if st.button("Generate Insights"):
    if not titles:
        st.warning("No articles to summarize.")
    elif not ollama:
        st.info("Ollama not available. Install and pull 'llama3.2' to enable.")
    else:
        prompt = "Summarize key AI trends from these articles:\n\n" + "\n".join(titles)
        try:
            resp = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
            st.write(resp.get("message", {}).get("content", "(No response)"))
        except Exception as e:
            st.error(f"Model error: {e}")


