# training/annotation_app.py — v2
# Run: streamlit run training/annotation_app.py
import sys, os, json, time, re
import streamlit as st
import pandas as pd
from groq import Groq

# Setup path and environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- CONFIGURATION & UI STYLING ---
st.set_page_config(
    page_title="DPDPA Annotation",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; background: #0f0f0f !important; color: #e0e0e0 }
.stApp { background: #0f0f0f !important }
#MainMenu, footer { display: none !important }
.stTextArea textarea { background: #1a1a1a !important; border: 1px solid #2a2a2a !important; border-radius: 8px !important; color: #e0e0e0 !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 13px !important }
.stButton>button { background: #6366f1 !important; color: #fff !important; border: none !important; border-radius: 8px !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 12px !important; font-weight: 600 !important; letter-spacing: .06em !important; padding: 12px 24px !important; width: 100% !important; text-transform: uppercase !important }
.stButton>button:hover { background: #4f52d0 !important }
.stButton>button:disabled { background: #222 !important; color: #555 !important }
[data-testid="metric-container"] { background: #1a1a1a !important; border: 1px solid #2a2a2a !important; border-radius: 8px !important; padding: 16px !important }
.mono { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #888; letter-spacing: .08em; text-transform: uppercase }
</style>""", unsafe_allow_html=True)

# --- CONSTANTS ---
DPDPA = {
    "S.4": ("Grounds for Processing", "Lawful purpose, consent, or legitimate use"),
    "S.5": ("Notice Requirement", "Must inform user: what data, why, who shared with"),
    "S.6": ("Consent", "Free, specific, informed, unconditional, unambiguous"),
    "S.7": ("Legitimate Uses", "Processing without consent: employment, state, legal"),
    "S.8": ("Obligations of Fiduciary", "Accuracy, security, erasure, accountability"),
    "S.9": ("Children's Data", "Parental consent; no tracking/profiling under 18"),
    "S.11": ("Withdrawal of Consent", "User can withdraw consent at any time"),
    "S.12": ("Grievance Redressal", "User can complain to Data Protection Board"),
    "S.13": ("Rights of Data Principal", "Access, correction, erasure, nomination"),
    "S.16": ("Data Protection Board", "Complaints, appeals, adjudication"),
    "S.17": ("Exemptions", "National security, research, legal proceedings"),
    "N/A": ("Not Applicable", "Does not relate to any DPDPA section")
}

CATS = {
    "data_collection": "What personal data is collected",
    "data_sharing": "Who data is shared with",
    "user_rights": "User rights: access, delete, correct, opt-out",
    "data_retention": "How long data is stored",
    "security": "Security measures or disclaimers",
    "policy_changes": "How/when the policy changes",
    "childrens_data": "Data from/about minors",
    "legal_jurisdiction": "Legal terms, arbitration, governing law",
    "general": "Introductory/definitional/scope clause"
}

RC = {"red": "#f87171", "green": "#4ade80", "gray": "#fbbf24"}
RI = {"red": "🔴", "green": "🟢", "gray": "🟡"}
PRIVACY_KW = ['data', 'information', 'personal', 'collect', 'share', 'use', 'privacy', 'policy', 'right', 'consent', 'access', 'delete', 'retain', 'store', 'process', 'disclose', 'transfer', 'security', 'cookie', 'third part', 'partner', 'purpose', 'account', 'grievance', 'officer', 'notify', 'breach', 'protect', 'location', 'device', 'identifier', 'profile', 'marketing']
JUNK_RE = [r'keyboard_arrow', r'^\s*\d+\s*$', r'access denied', r"you don.t have permission", r'^section \d+[\.\(].{0,60}(updated|added|clarif)', r'investment.*risk.*read all.*document', r'securities.*market.*subject to market', r'cashback.*incredible offers', r'buying power.*stocks.*interest rate', r'all rights reserved\s*$']

# --- LOGIC FUNCTIONS ---
def is_definite_junk(text):
    t = text.lower().strip()
    for p in JUNK_RE:
        if re.search(p, t):
            return True, f"Pattern: {p[:35]}"
    if text.count('\n') >= 2:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) >= 2 and all(len(l.split()) < 6 for l in lines):
            return True, "Address fragment"
    return False, ""

def junk_score(text, wc):
    s, w = 0.0, []
    t = text.lower()
    if wc < 10:
        s += 0.5
        w.append(f"Very short ({wc}w)")
    elif wc < 15:
        s += 0.2
        w.append(f"Short ({wc}w)")
    
    if not re.search(r'\b(is|are|was|were|will|may|can|shall|collect|share|use|store|process|have|has|retain|disclose)\b', t):
        s += 0.3
        w.append("No verb")
    if not any(k in t for k in PRIVACY_KW):
        s += 0.35
        w.append("No privacy keywords")
    if wc < 14 and not text.strip().endswith(('.', ',')):
        s += 0.15
        w.append("Fragment")
    if re.search(r'(insurance|cashback|download|get it on|available on|sign up|sign in)', t):
        s += 0.4
        w.append("Marketing")
    return round(min(s, 1.0), 2), w

def get_model():
    """Get Groq client using key from session state (entered in sidebar)."""
    k = st.session_state.get("groq_api_key", "").strip()
    if not k:
        return None, "No API key — enter your Groq key in the sidebar"
    try:
        return Groq(api_key=k), None
    except Exception as e:
        return None, f"Groq init error: {e}"


PROMPT = """You are an expert privacy law annotator for India's Digital Personal Data Protection Act 2023 (DPDPA).

Annotate the clause with THREE labels: category, risk_label, dpdpa_section.

=== CATEGORY (choose ONE) ===
data_collection    : What personal data is collected from the user
data_sharing       : Who data is shared with, sold to, or disclosed to
user_rights        : User rights — access, delete, correct, opt-out, grievance
data_retention     : How long data is stored or when it is deleted
security           : Security measures or disclaimers about data protection
policy_changes     : How or when the privacy policy itself may change
childrens_data     : Data about or from minors / children
legal_jurisdiction : Legal terms, governing law, applicable regulations, arbitration
general            : Introductory, definitional, or scope-setting clause

=== RISK_LABEL (choose ONE) ===
red   : Harms user — data sold/shared broadly, rights waived, indefinite retention, no advance notice of changes, mandatory arbitration, vague unlimited data use
green : Protects user — no selling, explicit consent required, clear user rights, defined retention, strong security, advance notice, opt-out available
gray  : Neutral/ambiguous — boilerplate, procedural, definitional, scope clause, mixed signals

=== DPDPA_SECTION — ALWAYS assign the most relevant section. Use N/A only if truly no section applies. ===
S.4  : Grounds for processing — lawful purpose, consent basis, legitimate use; scope of the Act; applicability to Indian companies; which laws govern data processing
S.5  : Notice requirement — company must inform user what data is collected, why, and who it is shared with
S.6  : Consent — free, specific, informed, unconditional, unambiguous consent before processing
S.7  : Legitimate uses — processing without consent (legal obligation, employment, state benefit, medical emergency)
S.8  : Obligations of data fiduciary — data accuracy, security safeguards, erasure of data, accountability, breach notification
S.9  : Children's data — parental/guardian consent required; prohibition on tracking or profiling children under 18
S.11 : Withdrawal of consent — user can withdraw consent at any time; effect of withdrawal
S.12 : Grievance redressal — mechanism for user complaints; grievance officer; time-bound resolution
S.13 : Rights of data principal — right to access, correction, erasure, nomination; how to exercise rights
S.16 : Data Protection Board — filing complaints, appeals, adjudication of disputes
S.17 : Exemptions — national security, public order, research/archiving, legal proceedings, journalistic purposes
N/A  : Only use when the clause is purely introductory boilerplate with zero connection to any DPDPA provision

=== SECTION MAPPING — follow this strictly ===
"what data we collect / why we collect it / notice to user" → S.5
"consent / by using this service you agree / agreement to terms" → S.6
"withdraw consent / opt out / unsubscribe" → S.11
"right to access / delete / correct / erase / nominate" → S.13
"security / encryption / breach notification / safeguards" → S.8
"children / minors / parental consent / under 18" → S.9
"grievance officer / complaint mechanism / contact for privacy" → S.12
"binding arbitration / class action waiver" → S.16
"governing law / applicable law / Indian laws apply / IT Act / Aadhaar Act / PDPA / which regulations govern" → S.4
"legitimate purpose / business purpose / legal obligation / court order" → S.7
"national security / research / journalism / legal proceedings" → S.17
"how long data is kept / retention period / deletion schedule" → S.8
"changes to this policy / updated policy" → S.5

=== CRITICAL RULE ===
N/A is a LAST RESORT. If the clause mentions ANY Indian law, regulation, legal framework,
IT Act, Aadhaar Act, governing jurisdiction, or legal compliance — use S.4 or S.17, NOT N/A.
If the clause mentions consent, use S.6. If it mentions user rights, use S.13.
When in doubt between two sections, pick the one most directly protecting the user.

Respond ONLY with valid JSON, no markdown, no extra text:
{"category":"...","risk_label":"...","dpdpa_section":"...","confidence":0.85,"reason":"one sentence why","user_impact":"one sentence plain English","flags":[]}"""

def call_gemini(text, company="", retries=4):
    client, err = get_model()
    if not client:
        return {"error": err or "No API key — enter your Groq key in the sidebar"}
    for attempt in range(retries):
        try:
            r = client.chat.completions.create(
                model    = "llama-3.3-70b-versatile",
                messages = [
                    {"role": "system", "content": PROMPT},
                    {"role": "user",   "content": f"Company:{company}\nClause:{text}"}
                ],
                temperature     = 0.1,
                max_tokens      = 300,
                response_format = {"type": "json_object"},
            )
            raw = r.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                raw = raw[4:] if raw.startswith("json") else raw
            res = json.loads(raw.strip())
            assert res.get('category') in CATS
            assert res.get('risk_label') in ('red', 'green', 'gray')
            assert res.get('dpdpa_section') in DPDPA
            return res
        except json.JSONDecodeError:
            time.sleep(2)
        except AssertionError:
            time.sleep(2)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower():
                wait = 65
                st.warning(f"Rate limited — waiting {wait}s for quota reset...")
                time.sleep(wait)
            elif "401" in err_str or "invalid_api_key" in err_str.lower() or "authentication" in err_str.lower():
                return {"error": f"Invalid API key — check your Groq key in the sidebar"}
            elif "404" in err_str or "model_not_found" in err_str.lower() or "does not exist" in err_str.lower():
                return {"error": f"Model not found — Groq may have updated available models: {err_str[:120]}"}
            elif "connection" in err_str.lower() or "network" in err_str.lower():
                return {"error": "Network error — check your internet connection"}
            else:
                # Show the REAL error so it can be debugged
                return {"error": f"API error: {err_str[:200]}"}
    return {"error": "All retries failed after 4 attempts — check sidebar for API key status"}

# --- SIDEBAR ---
with st.sidebar:
    # ── API KEY INPUT — safe, never saved to disk or git ──────
    st.markdown("<div style='font-family:IBM Plex Mono,monospace;font-size:11px;font-weight:700;color:#6366f1;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;'>GROQ API KEY</div>", unsafe_allow_html=True)
    api_key_input = st.text_input(
        "groq_key",
        value=st.session_state.get("groq_api_key", ""),
        type="password",
        placeholder="gsk_xxxxxxxxxxxxxxxxxxxx",
        label_visibility="collapsed",
        help="Free key from console.groq.com — never saved to disk"
    )
    if api_key_input:
        st.session_state["groq_api_key"] = api_key_input.strip()
        st.success("✓ Key saved for this session")
    else:
        st.warning("Paste Groq key above to annotate")
    st.markdown("<div style='font-size:10px;color:#444;font-family:IBM Plex Mono,monospace;margin-bottom:14px;'>Get free key: console.groq.com<br>Not saved to .env or any file</div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#1e1e1e;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:IBM Plex Mono,monospace;font-size:13px;font-weight:700;color:#6366f1;letter-spacing:.1em;text-transform:uppercase;margin-bottom:14px;'>DPDPA 2023</div>", unsafe_allow_html=True)
    for sec, (name, desc) in DPDPA.items():
        if sec == "N/A": continue
        st.markdown(f"<div style='background:#1a1a1a;border:1px solid #252525;border-radius:6px;padding:9px 11px;margin-bottom:5px;'><div style='font-family:IBM Plex Mono,monospace;font-size:11px;color:#6366f1;font-weight:600;'>{sec} — {name}</div><div style='font-size:11px;color:#555;margin-top:2px;'>{desc}</div></div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#1e1e1e;'><div style='font-family:IBM Plex Mono,monospace;font-size:11px;color:#444;line-height:1.9;'>🔴 RED = harms user<br>🟢 GREEN = protects user<br>🟡 GRAY = ambiguous<br><br>Junk ≥0.5 → review<br>Junk ≥0.8 → skip</div>", unsafe_allow_html=True)

# --- MAIN UI ---
st.markdown("<div style='padding:20px 0 8px;'><div style='font-family:IBM Plex Mono,monospace;font-size:20px;font-weight:700;color:#fff;'>DPDPA <span style='color:#6366f1;'>ANNOTATION</span> ASSISTANT <span style='font-size:11px;color:#333;'>v2</span></div><div style='font-size:13px;color:#555;margin-top:4px;'>Paste clause → annotation · Junk detection · Bulk CSV</div></div><hr style='border-color:#1a1a1a;margin:10px 0;'>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["// SINGLE CLAUSE", "// BULK ANNOTATE", "// JUNK REVIEW", "// CATEGORY GUIDE"])

# --- TAB 1: SINGLE CLAUSE ---
with tab1:
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.markdown('<div class="mono" style="margin-bottom:6px;">Clause Text</div>', unsafe_allow_html=True)
        cin = st.text_area("c", height=180, placeholder="Paste any privacy policy clause here...", label_visibility="collapsed")
        co = st.text_input("Company (optional)", placeholder="e.g. Zomato, PhonePe")
        if cin:
            wc = len(cin.split())
            jf, jr = is_definite_junk(cin)
            js, jw = junk_score(cin, wc)
            if jf:
                st.error(f"⚠️ DEFINITE JUNK — {jr}")
            elif js >= 0.5:
                st.warning(f"⚠️ Junk score {js:.0%} — {' · '.join(jw)}")
            else:
                st.success(f"✓ Valid · {wc} words · junk={js:.0%}")
        btn = st.button("⟶  ANALYZE CLAUSE", disabled=not bool(cin))

    with c2:
        st.markdown('<div class="mono" style="margin-bottom:6px;">Annotation Result</div>', unsafe_allow_html=True)
        if btn and cin:
            jf, jr = is_definite_junk(cin)
            if jf:
                st.error(f"Definite junk — skip.\n{jr}")
            else:
                with st.spinner("Calling Groq..."):
                    res = call_gemini(cin.strip(), co.strip())
                if "error" in res:
                    st.error(f"Error: {res['error']}")
                else:
                    risk = res.get("risk_label", "gray")
                    cat = res.get("category", "general")
                    sec = res.get("dpdpa_section", "N/A")
                    conf = float(res.get("confidence", 0))
                    reason = res.get("reason", "")
                    impact = res.get("user_impact", "")
                    flags = res.get("flags", [])
                    
                    rc2 = RC.get(risk, "#888")
                    ri2 = RI.get(risk, "⚪")
                    sn = DPDPA.get(sec, ("", ""))[0]
                    
                    a, b, c_ = st.columns(3)
                    with a:
                        st.markdown(f"<div style='background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:20px;text-align:center;min-height:80px;'><div class='mono'>CATEGORY</div><div style='font-size:12px;font-weight:600;color:#60a5fa;font-family:IBM Plex Mono,monospace;margin-top:8px;'>{cat.replace('_',' ').upper()}</div></div>", unsafe_allow_html=True)
                    with b:
                        st.markdown(f"<div style='background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:20px;text-align:center;min-height:80px;'><div class='mono'>RISK</div><div style='font-size:22px;margin-top:4px;'>{ri2}</div><div style='font-size:13px;font-weight:700;color:{rc2};font-family:IBM Plex Mono,monospace;'>{risk.upper()}</div></div>", unsafe_allow_html=True)
                    with c_:
                        st.markdown(f"<div style='background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:20px;text-align:center;min-height:80px;'><div class='mono'>DPDPA</div><div style='font-size:18px;font-weight:700;color:#a78bfa;font-family:IBM Plex Mono,monospace;margin-top:6px;'>{sec}</div><div style='font-size:10px;color:#555;'>{sn}</div></div>", unsafe_allow_html=True)
                    
                    cp = int(conf * 100)
                    cc = "#4ade80" if cp >= 80 else "#fbbf24" if cp >= 60 else "#f87171"
                    st.markdown(f"<div style='background:#1a1a1a;border:1px solid #222;border-radius:8px;padding:12px;margin-top:8px;'><div class='mono' style='margin-bottom:5px;'>CONFIDENCE — {cp}%</div><div style='background:#111;border-radius:2px;height:4px;'><div style='width:{cp}%;height:100%;background:{cc};border-radius:2px;'></div></div></div>", unsafe_allow_html=True)
                    
                    js2, _ = junk_score(cin, len(cin.split()))
                    if js2 >= 0.5:
                        st.markdown(f"<div style='background:#1a1000;border:1px solid #3d2500;border-radius:8px;padding:10px 14px;margin-top:8px;font-size:12px;color:#fbbf24;'>⚠️ Junk score {js2:.0%} — annotation may be unreliable. Consider skipping.</div>", unsafe_allow_html=True)
                    
                    if reason:
                        st.markdown(f"<div style='background:#111;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;padding:10px 14px;margin-top:8px;'><div class='mono' style='margin-bottom:3px;'>WHY</div><div style='font-size:13px;color:#ccc;'>{reason}</div></div>", unsafe_allow_html=True)
                    if impact:
                        st.markdown(f"<div style='background:#111;border-left:3px solid {rc2};border-radius:0 6px 6px 0;padding:10px 14px;margin-top:8px;'><div class='mono' style='margin-bottom:3px;'>PLAIN ENGLISH</div><div style='font-size:13px;color:#ccc;'>{impact}</div></div>", unsafe_allow_html=True)
                    if flags:
                        st.markdown(" ".join([f"<span style='background:#1e1e2e;border:1px solid #2d2d4a;border-radius:4px;padding:3px 8px;font-family:IBM Plex Mono,monospace;font-size:11px;color:#a78bfa;margin:2px;'>{f}</span>" for f in flags]), unsafe_allow_html=True)
                    
                    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
                    st.markdown('<div class="mono" style="margin-bottom:4px;">COPY TO SHEET</div>', unsafe_allow_html=True)
                    st.code(f"category: {cat}\nrisk_label: {risk}\ndpdpa_section: {sec}", language=None)
        else:
            st.markdown("<div style='background:#111;border:1px dashed #1e1e1e;border-radius:10px;padding:48px;text-align:center;color:#2a2a2a;font-family:IBM Plex Mono,monospace;font-size:12px;'>Paste a clause and click ANALYZE</div>", unsafe_allow_html=True)

# --- TAB 2: BULK ANNOTATE ---
with tab2:
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    st.markdown("<div style='background:#1a1a0a;border:1px solid #2d2500;border-radius:8px;padding:12px 16px;margin-bottom:14px;font-size:13px;color:#fbbf24;'>⚠️ Groq free tier: 30 req/min. Clauses above junk threshold auto-skipped. Results saved after every clause (crash-safe).</div>", unsafe_allow_html=True)
    up = st.file_uploader("Upload CSV", type=["csv"], key="b_up")
    
    if up:
        df = pd.read_csv(up, encoding='utf-8-sig')
        if 'junk_score' not in df.columns:
            df['junk_score'] = df.apply(lambda r: junk_score(str(r['text']), int(r.get('word_count', len(str(r['text']).split()))))[0], axis=1)
        
        skip_t = st.slider("Junk skip threshold", 0.3, 0.9, 0.6, 0.1)
        unann = df[df['category'].isna() | (df['category'] == '')]
        ann = df[~(df['category'].isna() | (df['category'] == ''))]
        will_ann = unann[unann['junk_score'] < skip_t]
        will_skip = unann[unann['junk_score'] >= skip_t]
        
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric("Total", len(df))
        with c2: st.metric("Done", len(ann))
        with c3: st.metric("To Annotate", len(will_ann))
        with c4: st.metric("Auto-Skipped", len(will_skip))
        with c5: st.metric("API Calls Saved", len(will_skip))
        
        st.dataframe(df.head(8)[['clause_id', 'company', 'text', 'word_count', 'junk_score']], use_container_width=True)
        cs, cb = st.columns(2)
        with cs: delay = st.slider("Delay (sec)", 1.0, 6.0, 2.0, 0.5)
        with cb: batch = st.slider("Clauses per run", 5, min(200, max(5, len(will_ann))), min(20, max(5, len(will_ann))), 5)
        
        if st.button(f"⟶  ANNOTATE {min(batch, len(will_ann))} CLAUSES"):
            client, err = get_model()
            if not client:
                st.error(f"API key error: {err}")
            elif len(will_ann) == 0:
                st.info("Nothing to annotate.")
            else:
                to_do = will_ann.head(batch)
                prog = st.progress(0)
                stat = st.empty()
                log = []
                for i, (idx, row) in enumerate(to_do.iterrows()):
                    js2, jw2 = junk_score(str(row['text']), int(row.get('word_count', 10)))
                    if js2 >= skip_t:
                        df.at[idx, 'category'] = 'SKIPPED_JUNK'
                        df.at[idx, 'risk_label'] = 'gray'
                        df.at[idx, 'dpdpa_section'] = 'N/A'
                        df.at[idx, 'notes'] = f"junk={js2} ({'; '.join(jw2)})"
                        log.append(f"[SKIP] {row.get('clause_id','')}: {str(row['text'])[:50]}")
                        prog.progress((i + 1) / len(to_do))
                        continue
                    
                    stat.markdown(f"<div class='mono'>[{i+1}/{len(to_do)}] {row.get('company','')} | {str(row['text'])[:55]}...</div>", unsafe_allow_html=True)
                    res = call_gemini(str(row['text']), str(row.get('company', '')))
                    
                    if "error" not in res:
                        df.at[idx, 'category'] = res.get('category', 'general')
                        df.at[idx, 'risk_label'] = res.get('risk_label', 'gray')
                        df.at[idx, 'dpdpa_section'] = res.get('dpdpa_section', 'N/A')
                        df.at[idx, 'notes'] = res.get('reason', '')
                        log.append(f"[OK]  {row.get('clause_id','')}: {res['category']}|{res['risk_label']}|{res['dpdpa_section']}")
                    else:
                        df.at[idx, 'notes'] = f"ERROR:{res['error']}"
                        log.append(f"[ERR] {row.get('clause_id','')}: {res['error']}")
                    
                    prog.progress((i + 1) / len(to_do))
                    time.sleep(delay)
                
                stat.markdown("<div class='mono' style='color:#4ade80;'>✓ Done</div>", unsafe_allow_html=True)
                with st.expander("Log"):
                    st.code('\n'.join(log), language=None)
                st.download_button("⬇  DOWNLOAD ANNOTATED CSV", data=df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), file_name="dpdpa_annotated.csv", mime="text/csv")
                
                from collections import Counter
                done_df = df[~(df['category'].isna() | (df['category'] == ''))]
                rcts = Counter(done_df['risk_label'])
                st.markdown(f"<div style='background:#111;border:1px solid #222;border-radius:8px;padding:12px;margin-top:10px;'><div class='mono' style='margin-bottom:6px;'>STATS — {len(done_df)} annotated</div><div style='font-size:13px;color:#ccc;'>🔴 Red:{rcts.get('red',0)} &nbsp;|&nbsp; 🟢 Green:{rcts.get('green',0)} &nbsp;|&nbsp; 🟡 Gray:{rcts.get('gray',0)}</div></div>", unsafe_allow_html=True)

# --- TAB 3: JUNK REVIEW ---
with tab3:
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    st.markdown("<div style='font-size:13px;color:#666;margin-bottom:14px;'>Upload CSV → scan for junk → review flagged clauses → download cleaned CSV.</div>", unsafe_allow_html=True)
    ju = st.file_uploader("Upload CSV to scan", type=["csv"], key="j_up")
    
    if ju:
        df_j = pd.read_csv(ju, encoding='utf-8-sig')
        scored = []
        for idx, row in df_j.iterrows():
            text = str(row['text'])
            wc = int(row.get('word_count', len(text.split())))
            dfj, djr = is_definite_junk(text)
            sc, wns = junk_score(text, wc)
            scored.append({'_idx': idx, 'clause_id': str(row.get('clause_id', '')), 'company': str(row.get('company', '')), 'text': text, 'definite': dfj, 'reason': djr, 'score': sc, 'warns': wns})
        
        defn = [r for r in scored if r['definite']]
        flagged = [r for r in scored if not r['definite'] and r['score'] >= 0.5]
        clean_j = [r for r in scored if not r['definite'] and r['score'] < 0.5]
        
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("🗑️ Definite Junk", len(defn))
        with c2: st.metric("⚠️ Needs Review", len(flagged))
        with c3: st.metric("✅ Clean", len(clean_j))
        
        if defn:
            st.markdown("#### 🗑️ Definite Junk — will be removed")
            for r in defn:
                st.markdown(f"<div style='background:#1a0808;border:1px solid #3d1515;border-radius:6px;padding:9px 12px;margin-bottom:5px;font-size:12px;'><span style='color:#f87171;font-family:IBM Plex Mono,monospace;'>[{r['company']}] [{r['reason']}]</span><br><span style='color:#666;'>{r['text'][:120]}</span></div>", unsafe_allow_html=True)
        
        kd = {}
        if flagged:
            st.markdown("#### ⚠️ Review These — Keep or Remove")
            for r in flagged:
                sc = r['score']
                scc = "#f87171" if sc >= 0.8 else "#fbbf24"
                ct, cb = st.columns([5, 1])
                with ct:
                    st.markdown(f"<div style='background:#141008;border:1px solid #2d2500;border-radius:6px;padding:10px 14px;'><div style='font-family:IBM Plex Mono,monospace;font-size:10px;color:{scc};margin-bottom:3px;'>[{r['company']}] {sc:.0%} — {' · '.join(r['warns'])}</div><div style='font-size:13px;color:#ccc;'>{r['text'][:160]}</div></div>", unsafe_allow_html=True)
                with cb:
                    dec = st.radio(f"d_{r['clause_id']}", ["Keep", "Remove"], index=1 if sc >= 0.7 else 0, key=f"jd_{r['clause_id']}", label_visibility="collapsed")
                    kd[r['clause_id']] = (dec == "Keep")
        
        if st.button("⟶  APPLY & DOWNLOAD CLEAN CSV"):
            rids = {r['clause_id'] for r in defn} | {r['clause_id'] for r in flagged if not kd.get(r['clause_id'], True)}
            df_c = df_j[~df_j['clause_id'].astype(str).isin(rids)].copy()
            st.success(f"✓ {len(df_c)} kept, {len(df_j)-len(df_c)} removed")
            st.download_button("⬇  DOWNLOAD CLEANED CSV", data=df_c.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), file_name="dpdpa_junk_cleaned.csv", mime="text/csv")

# --- TAB 4: CATEGORY GUIDE ---
with tab4:
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    examples = {
        "data_collection": ("We collect your name, email, GPS and device IDs.", "biometric, browsing history, cookies, IP"),
        "data_sharing": ("We share data with advertising partners for marketing.", "data brokers, affiliates, third parties"),
        "user_rights": ("You can request deletion of your data within 30 days.", "access, correction, erasure, opt-out, grievance"),
        "data_retention": ("We retain data 90 days after account deletion.", "indefinite, backup copies, legal hold"),
        "security": ("We use AES-256 and conduct annual pen tests.", "SSL, 2FA, ISO27001, breach notification"),
        "policy_changes": ("We may update this policy without prior notice.", "30-day notice, email alert, continued use = accept"),
        "childrens_data": ("We don't collect data from children under 18.", "parental consent, COPPA, age verification"),
        "legal_jurisdiction": ("Disputes resolved by binding arbitration.", "class action waiver, governing law, jurisdiction"),
        "general": ("This policy describes how we handle your info.", "scope, definitions, introduction, effective date")
    }
    for cat, (ex, kw) in examples.items():
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"<div style='background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;padding:14px;min-height:90px;'><div style='font-family:IBM Plex Mono,monospace;font-size:11px;color:#6366f1;font-weight:600;margin-bottom:5px;'>{cat.replace('_',' ').upper()}</div><div style='font-size:11px;color:#666;'>{CATS[cat]}</div><div style='font-size:10px;color:#333;margin-top:5px;font-family:IBM Plex Mono,monospace;'>{kw}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div style='background:#0f1a0f;border:1px solid #1a2a1a;border-radius:8px;padding:14px;min-height:90px;'><div style='font-size:10px;color:#333;font-family:IBM Plex Mono,monospace;margin-bottom:5px;'>EXAMPLE</div><div style='font-size:13px;color:#aaa;font-style:italic;'>\"{ex}\"</div></div>", unsafe_allow_html=True)
        st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### DPDPA 2023 Full Reference")
    for sec, (name, desc) in DPDPA.items():
        if sec == "N/A": continue
        st.markdown(f"<div style='background:#1a1a1a;border:1px solid #222;border-radius:8px;padding:12px 16px;margin-bottom:6px;display:flex;gap:18px;'><div style='font-family:IBM Plex Mono,monospace;font-size:14px;color:#a78bfa;font-weight:700;min-width:36px;'>{sec}</div><div><div style='font-size:13px;color:#ddd;font-weight:500;'>{name}</div><div style='font-size:12px;color:#555;margin-top:2px;'>{desc}</div></div></div>", unsafe_allow_html=True)