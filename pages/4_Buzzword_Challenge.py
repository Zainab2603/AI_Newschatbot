import streamlit as st
import random
from utils import inject_pastel_theme_css, render_shimmer_loader_css, inject_flip_card_css, BUZZWORDS

st.set_page_config(page_title="AI Buzzword Challenge", page_icon="🃏", layout="wide")
inject_pastel_theme_css()
render_shimmer_loader_css()
inject_flip_card_css()

st.title("AI Buzzword Challenge 🃏")
st.caption("Flip the cards to see definitions and fun facts.")

# Difficulty dropdown
difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Expert"], index=0)

# Shuffle cards each time
cards = BUZZWORDS.get(difficulty, []).copy()
random.shuffle(cards)

# Card grid wrapper
st.markdown("<div class='card-grid'>", unsafe_allow_html=True)

# Loop through buzzwords
# Shuffle cards each time
cards = BUZZWORDS.get(difficulty, []).copy()
random.shuffle(cards)

# Only take first 5 cards after shuffle
cards = cards[:5]

# Loop through buzzwords
for i, item in enumerate(cards):
    term = item["term"]
    definition = item["definition"]
    fun = item["fun_fact"]
    toggle_id = f"flip_{difficulty}_{i}"

    st.markdown(
        f"""
        <div class="flip-card">
            <input class="flip-toggle" id="{toggle_id}" type="checkbox" />
            <label for="{toggle_id}">
                <div class="flip-inner">
                    <!-- FRONT -->
                    <div class="flip-front">
                        <b>{term}</b>
                    </div>
                    <!-- BACK -->
                    <div class="flip-back">
                        <p><b>Definition:</b> {definition}</p>
                        <p style="margin-top:8px;"><b>Fun fact:</b> {fun}</p>
                    </div>
                </div>
            </label>
            <div class="flip-hint">Click to flip</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
