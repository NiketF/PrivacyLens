# frontend/app.py

import sys, os, html
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from src.pipeline import PrivacyPolicyAnalyzer

st.set_page_config(page_title="Privacy Lens", page_icon="🔍", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background: #0d0d0d !important;
    color: #e8e8e8;
}
#MainMenu, footer, header { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
.stApp { background: #0d0d0d !important; }

.stTextArea textarea {
    background: #141414 !important; border: 1px solid #2a2a2a !important;
    border-radius: 8px !important; color: #e8e8e8 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 13px !important; padding: 16px !important;
}
.stTextArea textarea:focus { border-color: #4ade80 !important; box-shadow: none !important; }
.stTextArea textarea::placeholder { color: #333 !important; }
.stTextInput input {
    background: #141414 !important; border: 1px solid #2a2a2a !important;
    border-radius: 8px !important; color: #e8e8e8 !important;
    font-family: 'IBM Plex Mono', monospace !important; font-size: 13px !important;
}
.stTextInput input:focus { border-color: #4ade80 !important; box-shadow: none !important; }

.stButton > button {
    background: #4ade80 !important; color: #0d0d0d !important;
    border: none !important; border-radius: 8px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important; font-weight: 700 !important;
    letter-spacing: 0.08em !important; padding: 14px 32px !important;
    width: 100% !important; text-transform: uppercase !important;
}
.stButton > button:hover { background: #22c55e !important; }
.stButton > button:disabled { background: #0d1f0d !important; color: #1a3d1a !important; }

.stTabs [data-baseweb="tab-list"] {
    background: transparent !important; border-bottom: 1px solid #222 !important; gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; border: none !important;
    border-bottom: 2px solid transparent !important; border-radius: 0 !important;
    color: #888 !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; font-weight: 600 !important;
    letter-spacing: 0.08em !important; margin-bottom: -1px !important;
    padding: 12px 18px !important; text-transform: uppercase !important;
}
.stTabs [aria-selected="true"] {
    color: #4ade80 !important; border-bottom: 2px solid #4ade80 !important;
    background: transparent !important; box-shadow: none !important;
}

[data-testid="metric-container"] {
    background: #111 !important; border: 1px solid #222 !important;
    border-radius: 10px !important; padding: 16px 20px !important;
}
[data-testid="metric-container"] label {
    color: #555 !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; text-transform: uppercase !important; letter-spacing: 0.1em !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #e8e8e8 !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 28px !important; font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

# ── LOAD MODEL ───────────────────────────────────────────────
@st.cache_resource
def load_analyzer():
    return PrivacyPolicyAnalyzer()

try:
    analyzer = load_analyzer()
except FileNotFoundError:
    st.error("Model not found. Run: python src/models/baseline_svm.py")
    st.stop()

# ── TOPBAR ───────────────────────────────────────────────────
st.markdown("""
<div style="background:#0d0d0d;border-bottom:1px solid #1a1a1a;
            padding:18px 48px;display:flex;align-items:center;justify-content:space-between;">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:17px;
                font-weight:700;color:#fff;letter-spacing:0.04em;">
        PRIVACY<span style="color:#4ade80;">LENS</span>
    </div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                color:#999;letter-spacing:0.14em;text-transform:uppercase;">
        AI-Powered Policy Analysis · v1.0
    </div>
</div>
""", unsafe_allow_html=True)

# ── HERO ─────────────────────────────────────────────────────
st.markdown("""
<div style="padding:56px 48px 36px;border-bottom:1px solid #1a1a1a;">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:38px;
                font-weight:700;color:#fff;line-height:1.1;margin-bottom:16px;">
        Know what you're<br>agreeing <span style="color:#4ade80;">to.</span>
    </div>
    <div style="font-size:14px;color:#aaa;max-width:520px;line-height:1.8;">
        Paste any privacy policy. Get a plain-English breakdown of what the
        company does with your data — classified by risk level.
    </div>
</div>
""", unsafe_allow_html=True)

# ── INPUT ────────────────────────────────────────────────────
st.markdown('<div style="padding:36px 48px;border-bottom:1px solid #1a1a1a;">', unsafe_allow_html=True)

tab_paste, tab_url = st.tabs(["// PASTE TEXT", "// FETCH FROM URL"])

policy_text = ""

with tab_paste:
    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
    policy_text = st.text_area(
        "Policy text", height=180,
        placeholder="Paste any privacy policy here...\n\nTip: Go to website → find Privacy Policy → Ctrl+A → Ctrl+C → paste here",
        label_visibility="collapsed"
    )
    if policy_text:
        wc = len(policy_text.split())
        st.markdown(
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:11px;'
            f'color:#999;margin-top:6px;">{wc:,} words · ready</div>',
            unsafe_allow_html=True)

with tab_url:
    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
    url = st.text_input("URL", placeholder="https://www.zomato.com/privacy", label_visibility="collapsed")
    fc, nc = st.columns([1,3])
    with fc:
        fetch_btn = st.button("FETCH", use_container_width=True)
    with nc:
        st.markdown(
            '<div style="font-family:IBM Plex Mono,monospace;font-size:11px;'
            'color:#888;padding-top:14px;">JS sites may need manual paste</div>',
            unsafe_allow_html=True)
    if fetch_btn and url:
        with st.spinner("Fetching..."):
            try:
                import requests
                from bs4 import BeautifulSoup
                resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
                soup = BeautifulSoup(resp.text, 'html.parser')
                for t in soup.find_all(['nav','header','footer','script','style']): t.decompose()
                main = soup.find('main') or soup.find('article') or soup.find('body')
                policy_text = main.get_text('\n', strip=True) if main else ""
                if len(policy_text) > 300:
                    st.success(f"Fetched {len(policy_text):,} chars")
                else:
                    st.warning("Too short — try pasting manually.")
            except Exception as e:
                st.error(f"Failed: {e}")

st.markdown('</div>', unsafe_allow_html=True)

_, bc, _ = st.columns([1,2,1])
with bc:
    analyze = st.button("⟶  ANALYZE POLICY", disabled=not bool(policy_text))

# ── RESULTS ──────────────────────────────────────────────────
if analyze and policy_text:
    with st.spinner("Classifying clauses..."):
        res = analyzer.analyze(policy_text, simplify_red=True)

    score = res['risk_score']
    level = res['risk_level']

    if   score <= 20: sc = "#4ade80"
    elif score <= 45: sc = "#fbbf24"
    elif score <= 70: sc = "#f87171"
    else:             sc = "#dc2626"

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    # ── SCORE ROW ─────────────────────────────────────────────
    st.markdown(f"""
    <div style="padding:0 48px;margin-bottom:24px;">
        <div style="background:#111;border:1px solid #222;border-radius:12px;
                    padding:28px 32px;display:inline-block;min-width:220px;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                        letter-spacing:0.14em;text-transform:uppercase;color:#aaa;margin-bottom:8px;">
                Overall Risk Score
            </div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:60px;
                        font-weight:700;color:{sc};line-height:1;">
                {int(score)}<span style="font-size:20px;color:#777;">/100</span>
            </div>
            <div style="background:#1a1a1a;border-radius:2px;height:3px;margin:14px 0 12px;">
                <div style="width:{score}%;height:100%;background:{sc};border-radius:2px;"></div>
            </div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;
                        font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:{sc};">
                {level}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Stat metrics
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1: st.metric("Clauses Analyzed", res['total_clauses'])
    with mc2: st.metric("🚩 High Risk",      res['red_count'])
    with mc3: st.metric("✅ Protective",      res['green_count'])
    with mc4: st.metric("⚠️ Ambiguous",       res['gray_count'])

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    # ── MISSING RIGHTS ────────────────────────────────────────
    if res['missing_rights']:
        st.warning(
            "**⚠ Rights absent from this policy:**\n" +
            "\n".join(f"- {r}" for r in res['missing_rights'])
        )
    else:
        st.success("✓ All key user rights are mentioned in this policy.")

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    # ── SINGLE CLAUSE CARD RENDERER (no HTML string building) ─
    def render_one_clause(c):
        risk  = c['risk_label']
        cat   = c['category'].replace('_',' ').title()
        conf  = c['risk_confidence']
        vague = c['vagueness']
        text  = c['text']
        expl  = c.get('explanation','').strip()

        border = {"red":"#3d1515","green":"#153d15","gray":"#2d2500"}.get(risk,"#222")
        bg     = {"red":"#120808","green":"#080f08","gray":"#111008"}.get(risk,"#111")
        icon   = {"red":"🚩","green":"✅","gray":"⚠️"}.get(risk,"·")
        label  = {"red":"HIGH RISK","green":"SAFE","gray":"UNCLEAR"}.get(risk,"")
        lcolor = {"red":"#f87171","green":"#4ade80","gray":"#fbbf24"}.get(risk,"#888")

        vague_str = " · ⚠ VAGUE" if vague > 0.35 else ""

        # Use st.container + st.markdown for each card individually
        with st.container():
            st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:8px;
            padding:16px 18px;margin-bottom:10px;">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:700;
                letter-spacing:0.12em;text-transform:uppercase;color:{lcolor};margin-bottom:8px;">
        {icon} {label}
    </div>
    <div style="font-size:13px;color:#ccc;line-height:1.7;margin-bottom:8px;">
        {html.escape(text)}
    </div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#999;">
        {cat} · {conf:.0%} confidence · {vague:.0%} vague{vague_str}
    </div>
</div>""", unsafe_allow_html=True)

            # Plain English as separate st.info call — never inside HTML string
            if expl:
                st.info(f"💡 **Plain English:** {expl}")

    def render_section(clauses, empty_msg):
        if not clauses:
            st.markdown(
                f'<div style="text-align:center;padding:48px;font-family:IBM Plex Mono,monospace;'
                f'font-size:12px;color:#888;letter-spacing:0.1em;">{empty_msg}</div>',
                unsafe_allow_html=True)
            return
        for c in clauses:
            render_one_clause(c)

    # ── THREE COLUMN FLAG VIEW ────────────────────────────────
    st.markdown("""
    <div style="padding:0 48px;margin-bottom:8px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.14em;
                    text-transform:uppercase;color:#777;margin-bottom:4px;">Policy Breakdown</div>
        <div style="font-size:13px;color:#aaa;">
            Every clause classified. Red = risk. Green = protected. Gray = unclear.
        </div>
    </div>
    """, unsafe_allow_html=True)

    red_clauses   = res['watch_out']
    green_clauses = [c for c in res['all_clauses'] if c['risk_label'] == 'green']
    gray_clauses  = [c for c in res['all_clauses'] if c['risk_label'] == 'gray']

    col_r, col_g, col_g2 = st.columns(3)

    with col_r:
        st.markdown(f"""
        <div style="background:#1a0808;border:1px solid #3d1515;border-radius:10px 10px 0 0;
                    padding:14px 18px;display:flex;align-items:center;gap:10px;">
            <span style="font-size:16px;">🚩</span>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:700;
                         letter-spacing:0.1em;text-transform:uppercase;color:#f87171;">Red Flag</span>
            <span style="margin-left:auto;font-family:'IBM Plex Mono',monospace;
                         font-size:11px;color:#a87070;">{len(red_clauses)} clauses</span>
        </div>
        <div style="border:1px solid #3d1515;border-top:none;border-radius:0 0 10px 10px;
                    padding:12px;min-height:200px;">
        </div>
        """, unsafe_allow_html=True)
        render_section(red_clauses, "NO HIGH-RISK CLAUSES")

    with col_g:
        st.markdown(f"""
        <div style="background:#0a1a0a;border:1px solid #153d15;border-radius:10px 10px 0 0;
                    padding:14px 18px;display:flex;align-items:center;gap:10px;">
            <span style="font-size:16px;">✅</span>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:700;
                         letter-spacing:0.1em;text-transform:uppercase;color:#4ade80;">Green Flag</span>
            <span style="margin-left:auto;font-family:'IBM Plex Mono',monospace;
                         font-size:11px;color:#70a870;">{len(green_clauses)} clauses</span>
        </div>
        <div style="border:1px solid #153d15;border-top:none;border-radius:0 0 10px 10px;
                    padding:12px;min-height:200px;">
        </div>
        """, unsafe_allow_html=True)
        render_section(green_clauses, "NO PROTECTIVE CLAUSES")

    with col_g2:
        st.markdown(f"""
        <div style="background:#141008;border:1px solid #2d2500;border-radius:10px 10px 0 0;
                    padding:14px 18px;display:flex;align-items:center;gap:10px;">
            <span style="font-size:16px;">⚠️</span>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:700;
                         letter-spacing:0.1em;text-transform:uppercase;color:#fbbf24;">Gray Flag</span>
            <span style="margin-left:auto;font-family:'IBM Plex Mono',monospace;
                         font-size:11px;color:#a89050;">{len(gray_clauses)} clauses</span>
        </div>
        <div style="border:1px solid #2d2500;border-top:none;border-radius:0 0 10px 10px;
                    padding:12px;min-height:200px;">
        </div>
        """, unsafe_allow_html=True)
        render_section(gray_clauses, "NO AMBIGUOUS CLAUSES")

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ── DETAIL TABS ───────────────────────────────────────────
    st.markdown(
        '<div style="padding:0 48px 4px;">'
        '<div style="font-family:IBM Plex Mono,monospace;font-size:10px;'
        'letter-spacing:0.14em;text-transform:uppercase;color:#777;">Detailed Breakdown</div>'
        '</div>',
        unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs([
        f"📦 Data Collected ({len(res['data_collected'])})",
        f"🤝 Shared With ({len(res['data_shared'])})",
        f"🛡 Your Rights ({len(res['user_rights'])})",
        f"📋 All Clauses ({res['total_clauses']})",
    ])

    with t1: render_section(res['data_collected'], "NO DATA COLLECTION CLAUSES FOUND")
    with t2: render_section(res['data_shared'],    "NO DATA SHARING CLAUSES FOUND")
    with t3: render_section(res['user_rights'],    "NO USER RIGHTS CLAUSES FOUND")
    with t4: render_section(res['all_clauses'],    "NO CLAUSES FOUND")

    # ── FOOTER ────────────────────────────────────────────────
    st.markdown(f"""
    <div style="padding:20px 48px;border-top:1px solid #1a1a1a;margin-top:32px;
                font-family:'IBM Plex Mono',monospace;font-size:11px;color:#666;
                letter-spacing:0.06em;">
        {res['total_clauses']} clauses analyzed &nbsp;·&nbsp;
        TF-IDF + SVM &nbsp;·&nbsp; Macro F1: 0.80 &nbsp;·&nbsp;
        PrivacyLens v1.0
    </div>
    """, unsafe_allow_html=True)