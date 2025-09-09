import streamlit as st

from utils import inject_pastel_theme_css, render_shimmer_loader_css


st.set_page_config(page_title="Chatbot", page_icon="💬", layout="wide")
inject_pastel_theme_css()
render_shimmer_loader_css()


st.title("Chatbot")
mode = st.toggle("Debate Mode", value=False)
user_input = st.text_area("Ask about AI or paste an article for debate:", height=140)

# Try to load Ollama
ollama_client = None
try:
    import ollama  # type: ignore
    ollama_client = ollama
except Exception:
    ollama_client = None


DEFAULT_MODEL = "llama3.2"  # default model as requested


def call_llama_stream(prompt: str, model: str = DEFAULT_MODEL):
    if not ollama_client:
        yield "(Local Llama not available. Install Ollama and pull 'llama3.2' to enable responses.)"
        return
    try:
        stream = ollama_client.chat(model=model, messages=[{"role": "user", "content": prompt}], stream=True)
        for chunk in stream:
            delta = chunk.get("message", {}).get("content", "")
            if delta:
                yield delta
    except Exception as e:  # pragma: no cover
        yield f"(Model error: {e})"


if st.button("Generate"):
    if not user_input.strip():
        st.warning("Please enter a question or article text.")
    else:
        if not mode:
            # Q&A mode with streaming
            container = st.empty()
            accumulated = ""
            for chunk in call_llama_stream(user_input):
                accumulated += chunk
                container.markdown(f"<div class='news-card' style='background:#e7f0ff'><b>Answer:</b><br>{accumulated}</div>", unsafe_allow_html=True)
        else:
            prompt = (
                "Act as two debaters. Person A defends this news/article. Person B criticizes it. "
                "Use short, engaging points.\n\nText:\n" + user_input
            )
            # Stream into a buffer, then render split bubbles to keep the same UI
            accumulated = ""
            placeholder = st.empty()
            for chunk in call_llama_stream(prompt):
                accumulated += chunk
                # show a live combined transcript while streaming
                placeholder.markdown(
                    f"<div class='news-card'><b>Debate (streaming)...</b><br>{accumulated}</div>",
                    unsafe_allow_html=True,
                )
            placeholder.empty()
            if accumulated.startswith("(Local Llama not available"):
                st.markdown(
                    """
                    <div class='news-card'>
                        <div style='display:flex; gap:10px; flex-wrap:wrap;'>
                            <div style='flex:1; min-width:280px; background:#dff3ea; padding:10px; border-radius:12px;'>
                                <b>Pro (green):</b>
                                <ul><li>Potential productivity gains</li><li>New AI products</li><li>Accessibility</li></ul>
                            </div>
                            <div style='flex:1; min-width:280px; background:#ffe2ea; padding:10px; border-radius:12px;'>
                                <b>Con (pink):</b>
                                <ul><li>Bias & safety risks</li><li>Job displacement</li><li>Privacy concerns</li></ul>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                parts = accumulated.split("\n\n")
                pro = parts[0] if parts else accumulated
                con = parts[1] if len(parts) > 1 else ""
                st.markdown(
                    f"<div class='news-card' style='background:#dff3ea'><b>Pro:</b><br>{pro}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='news-card' style='background:#ffe2ea'><b>Con:</b><br>{con}</div>",
                    unsafe_allow_html=True,
                )


