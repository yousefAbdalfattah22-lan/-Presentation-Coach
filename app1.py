import os
import re
import html

import requests
import streamlit as st


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Presentation Coach",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# API SETTINGS  (من secrets أو متغيرات البيئة - مش مكتوبة في الكود)
# =========================================================
# ملف .streamlit/secrets.toml:
#   BASE_URL = "https://xxxx.ngrok-free.app"
#   API_KEY  = "secret123"

def get_config(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


BASE_URL = "https://uprising-education-overcoat.ngrok-free.dev"
API_KEY = "secret123"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "ngrok-skip-browser-warning": "true",
}


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
<style>
    .stApp { background: #0b1020; color: #f8fafc; }

    section[data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #263244;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        background: linear-gradient(135deg, #111827, #172554);
        border: 1px solid #263244;
        border-radius: 22px;
        padding: 32px;
        margin-bottom: 25px;
        box-shadow: 0 10px 35px rgba(0, 0, 0, 0.25);
    }
    .hero-title { font-size: 42px; font-weight: 800; margin-bottom: 8px; }
    .hero-subtitle { color: #aeb8ca; font-size: 17px; line-height: 1.6; }

    .card-title { font-size: 20px; font-weight: 700; margin: 10px 0 12px; }

    .question-box {
        background: #172554;
        border: 1px solid #3157a5;
        border-radius: 18px;
        padding: 25px;
        margin: 10px 0 20px;
    }
    .question-label {
        color: #93c5fd;
        font-size: 14px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .question-text {
        font-size: 23px;
        font-weight: 600;
        line-height: 1.5;
        margin-top: 8px;
    }

    .score-card {
        background: #111827;
        border: 1px solid #263244;
        border-radius: 18px;
        padding: 25px;
        text-align: center;
    }
    .score-number { font-size: 52px; font-weight: 800; }
    .score-label { color: #94a3b8; font-size: 14px; }

    .stButton > button { border-radius: 12px; font-weight: 700; min-height: 45px; }

    .stTextInput input, .stTextArea textarea {
        background: #0f172a;
        color: white;
        border: 1px solid #334155;
        border-radius: 12px;
    }

    hr { border-color: #263244; }
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "question": "",
    "evaluation": "",
    "score": None,
    "questions_answered": 0,
    "scores": [],
    "topic_input": "",
    "answer": "",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# API FUNCTIONS
# =========================================================

def call_api(endpoint: str, payload: dict, field: str) -> str:
    """Send a POST request and return the `field` from the JSON reply.
    Any problem is returned as a string starting with 'ERROR'."""

    if not BASE_URL or "PUT_YOUR" in BASE_URL:
        return "ERROR: BASE_URL is not configured (set it in secrets.toml or env)."

    try:
        response = requests.post(
            BASE_URL.rstrip("/") + endpoint,
            headers=HEADERS,
            json=payload,
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()

        if field not in data:
            return f"ERROR: Unexpected server response (missing '{field}')."

        return str(data[field])

    except requests.exceptions.Timeout:
        return "ERROR: The AI server took too long to respond."
    except requests.exceptions.RequestException as e:
        return f"ERROR: {e}"
    except ValueError:
        return "ERROR: Server did not return valid JSON (check the ngrok URL)."


def generate_question(topic: str) -> str:
    return call_api("/question", {"topic": topic}, "question")


def evaluate_answer(topic: str, question: str, answer: str) -> str:
    return call_api(
        "/evaluate",
        {"topic": topic, "question": question, "answer": answer},
        "evaluation",
    )


def extract_score(text: str):
    """Find 'SCORE: 7/10' even with markdown like **SCORE:** 7/10."""
    match = re.search(
        r"SCORE[\s\*]*:[\s\*]*(\d+(?:\.\d+)?)\s*/\s*10",
        text,
        re.IGNORECASE,
    )
    return float(match.group(1)) if match else None


def request_new_question():
    """Shared logic for both question buttons."""
    topic = st.session_state.topic_input.strip()

    if not topic:
        st.warning("Please enter your presentation topic first.")
        return

    with st.spinner("🤖 AI is preparing a question..."):
        question = generate_question(topic)

    if question.startswith("ERROR"):
        st.error(question)
        return

    st.session_state.question = question
    st.session_state.evaluation = ""
    st.session_state.score = None
    st.session_state.answer = ""  # clear the previous answer


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("## 🎤 Presentation Coach")

    st.markdown(
        """
        Practice your presentation with AI.

        **Workflow**

        1. Choose your topic
        2. Get an audience question
        3. Answer it
        4. Receive AI feedback
        """
    )

    st.divider()
    st.markdown("### 📊 Session")

    st.metric("Questions Answered", st.session_state.questions_answered)

    if st.session_state.scores:
        average = sum(st.session_state.scores) / len(st.session_state.scores)
        st.metric("Average Score", f"{average:.1f}/10")

    st.divider()

    if st.button("🔄 Reset Session", width="stretch"):
        for key, value in defaults.items():
            st.session_state[key] = [] if isinstance(value, list) else value
        st.rerun()


# =========================================================
# HERO
# =========================================================

st.markdown(
    """
<div class="hero">
    <div class="hero-title">🎤 Presentation Coach</div>
    <div class="hero-subtitle">
        Practice your presentation, answer realistic questions,
        and get instant AI-powered feedback on your performance.
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# =========================================================
# TOPIC
# =========================================================

st.markdown('<div class="card-title">📚 Presentation Topic</div>', unsafe_allow_html=True)

st.text_input(
    "Enter your presentation topic",
    key="topic_input",
    placeholder="Example: Artificial Intelligence",
)


# =========================================================
# GENERATE QUESTION
# =========================================================

col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🎯 Generate Audience Question", width="stretch"):
        request_new_question()

with col2:
    if st.session_state.question:
        if st.button("🆕 New Question", width="stretch"):
            request_new_question()


# =========================================================
# QUESTION + ANSWER
# =========================================================

if st.session_state.question:

    # كل المحتوى جوه نفس الـ HTML عشان الـ div ما يتقطعش
    safe_question = html.escape(st.session_state.question)

    st.markdown(
        f"""
<div class="question-box">
    <div class="question-label">Audience Question</div>
    <div class="question-text">{safe_question}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="card-title">🎤 Your Answer</div>', unsafe_allow_html=True)

    st.text_area(
        "Answer the question as if you are presenting.",
        key="answer",
        height=220,
        placeholder="Write your answer here...\n\nTry to answer naturally and clearly.",
    )

    if st.button("📊 Evaluate My Answer", width="stretch"):
        answer = st.session_state.answer

        if not answer.strip():
            st.warning("Please write your answer first.")
        else:
            with st.spinner("🤖 AI is evaluating your answer..."):
                evaluation = evaluate_answer(
                    st.session_state.topic_input,
                    st.session_state.question,
                    answer,
                )

            if evaluation.startswith("ERROR"):
                st.error(evaluation)
            else:
                st.session_state.evaluation = evaluation
                st.session_state.questions_answered += 1

                score = extract_score(evaluation)
                st.session_state.score = score  # None لو مفيش سكور

                if score is not None:
                    st.session_state.scores.append(score)


# =========================================================
# FEEDBACK
# =========================================================

if st.session_state.evaluation:

    st.divider()
    st.markdown('<div class="card-title">📊 AI Performance Feedback</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        score = st.session_state.score
        score_text = f"{score:g}/10" if score is not None else "—"

        st.markdown(
            f"""
<div class="score-card">
    <div class="score-number">{score_text}</div>
    <div class="score-label">Presentation Score</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with c2:
        st.metric("Questions Answered", st.session_state.questions_answered)

    with c3:
        if st.session_state.scores:
            average = sum(st.session_state.scores) / len(st.session_state.scores)
            st.metric("Average Score", f"{average:.1f}/10")

    if st.session_state.score is None:
        st.info("Couldn't find a score in the feedback, so it wasn't counted in your average.")

    # الـ feedback جوه container حقيقي بدل div مقسوم على أكتر من استدعاء
    with st.container(border=True):
        st.markdown(st.session_state.evaluation)


# =========================================================
# FOOTER
# =========================================================

st.markdown("<br><br>", unsafe_allow_html=True)

st.markdown(
    """
<div style="text-align:center; color:#64748b; font-size:13px;">
    🎤 Presentation Coach • Powered by AI
</div>
""",
    unsafe_allow_html=True,
)
