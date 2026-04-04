import streamlit as st
import requests
import json
import time
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nango API Explorer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Syne:wght@400;600;800&display=swap');

/* ── Global dark background with grid ── */
html, body, [class*="css"], .stApp {
    font-family: 'Syne', sans-serif;
    background-color: #0a0c10 !important;
}
.stApp {
    background-image:
        linear-gradient(rgba(42,92,255,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(42,92,255,0.04) 1px, transparent 1px) !important;
    background-size: 40px 40px !important;
    background-attachment: fixed !important;
}
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 4rem;
    background: transparent !important;
}
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="column"],
section.main > div {
    background: transparent !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid #1e2530 !important;
}
section[data-testid="stSidebar"] > div { background: #0d1117 !important; }
section[data-testid="stSidebar"] * { color: #c9d1d9; }
section[data-testid="stSidebar"] .stTextInput input {
    background: #111318 !important;
    border: 1px solid #22262f !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    color: #e8ecf4 !important;
}
section[data-testid="stSidebar"] .stTextInput input:focus {
    border-color: #2a5cff !important;
    box-shadow: 0 0 0 3px rgba(42,92,255,0.15) !important;
}
section[data-testid="stSidebar"] label {
    color: #6b7280 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
}

/* ── Main text inputs ── */
.stTextInput input {
    background: #111318 !important;
    border: 1px solid #22262f !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    color: #e8ecf4 !important;
}
.stTextInput input:focus {
    border-color: #2a5cff !important;
    box-shadow: 0 0 0 3px rgba(42,92,255,0.15) !important;
}
.stTextInput label {
    color: #6b7280 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #0d1117 0%, #111318 100%);
    border: 1px solid #22262f;
    border-radius: 14px;
    padding: 26px 30px;
    margin-bottom: 22px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #2a5cff, #00d97e, transparent);
}
.hero-row { display:flex; align-items:center; gap:14px; }
.hero-logo {
    width:44px; height:44px; background:#2a5cff; border-radius:10px;
    display:flex; align-items:center; justify-content:center;
    font-family:'JetBrains Mono',monospace; font-size:18px; font-weight:700; color:white;
    box-shadow:0 0 24px rgba(42,92,255,0.5); flex-shrink:0;
}
.hero-title { font-family:'Syne',sans-serif; font-size:24px; font-weight:800; color:#e8ecf4; letter-spacing:-0.5px; margin:0; }
.hero-sub   { font-family:'JetBrains Mono',monospace; font-size:11px; color:#4d7cff; margin-top:3px; letter-spacing:1px; }
.hero-dot   { margin-left:auto; display:flex; align-items:center; gap:8px; font-family:'JetBrains Mono',monospace; font-size:11px; color:#6b7280; }
.live-dot   { width:8px; height:8px; border-radius:50%; background:#00d97e; box-shadow:0 0 8px #00d97e; animation:blink 2s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* ── Panels ── */
.panel-card, .curl-panel {
    background: #111318;
    border: 1px solid #22262f;
    border-radius: 14px;
    padding: 22px 24px;
    position: relative;
    overflow: hidden;
    height: 100%;
}
.panel-card::before {
    content: ''; position:absolute; top:0; left:0; right:0; height:1px;
    background: linear-gradient(90deg, transparent, rgba(42,92,255,0.5), transparent);
}
.curl-panel::before {
    content: ''; position:absolute; top:0; left:0; right:0; height:1px;
    background: linear-gradient(90deg, transparent, rgba(0,217,126,0.4), transparent);
}
.panel-label {
    font-family:'JetBrains Mono',monospace; font-size:10px; color:#4d7cff;
    letter-spacing:2px; text-transform:uppercase; margin-bottom:14px;
    display:flex; align-items:center; gap:8px;
}
.panel-label::after { content:''; flex:1; height:1px; background:#22262f; }
.curl-header {
    font-family:'JetBrains Mono',monospace; font-size:10px; color:#00d97e;
    letter-spacing:2px; text-transform:uppercase; margin-bottom:14px;
    display:flex; align-items:center; gap:8px;
}
.curl-header::after { content:''; flex:1; height:1px; background:#22262f; }

/* ── cURL box ── */
.curl-box {
    background: #0a0c10;
    border: 1px solid #22262f;
    border-radius: 10px;
    padding: 18px 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    line-height: 2;
    color: #8b949e;
    white-space: pre;
    overflow-x: auto;
}
.curl-box .kw   { color:#ffa657; }
.curl-box .flag { color:#00d97e; }
.curl-box .url  { color:#4d7cff; }
.curl-box .val  { color:#e8ecf4; }

/* ── Button ── */
.stButton > button {
    background: #2a5cff !important; color: white !important;
    border: none !important; border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 600 !important; font-size: 13px !important;
    letter-spacing: 0.5px !important; padding: 10px 28px !important;
    width: 100%; box-shadow: 0 0 20px rgba(42,92,255,0.3) !important;
}
.stButton > button:hover {
    background: #4d7cff !important;
    box-shadow: 0 0 32px rgba(42,92,255,0.5) !important;
}

/* ── Badges ── */
.badge { display:inline-block; padding:3px 12px; border-radius:20px; font-family:'JetBrains Mono',monospace; font-size:12px; font-weight:600; }
.badge-ok  { background:#00d97e18; color:#00d97e; border:1px solid #00d97e55; }
.badge-err { background:#ff4d6a18; color:#ff4d6a; border:1px solid #ff4d6a55; }

/* ── Metrics ── */
.metric-row { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px; }
.metric-box { background:#111318; border:1px solid #22262f; border-radius:8px; padding:10px 18px; font-family:'JetBrains Mono',monospace; }
.metric-title { font-size:10px; color:#484f58; text-transform:uppercase; letter-spacing:1px; }
.metric-val   { font-size:18px; font-weight:700; color:#e8ecf4; margin-top:2px; }
.url-bar { font-family:'JetBrains Mono',monospace; font-size:11px; color:#484f58; background:#0a0c10; border:1px solid #22262f; border-radius:8px; padding:10px 14px; margin-bottom:16px; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background:#0a0c10 !important; border-radius:10px 10px 0 0;
    gap:4px; padding:6px 6px 0; border-bottom:1px solid #22262f;
}
.stTabs [data-baseweb="tab"] {
    background:transparent !important; border-radius:7px 7px 0 0 !important;
    font-family:'JetBrains Mono',monospace !important; font-size:12px !important;
    color:#484f58 !important; border-bottom:2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    background:#111318 !important; color:#e8ecf4 !important;
    border-bottom:2px solid #2a5cff !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background:#111318 !important; border:1px solid #22262f;
    border-top:none; border-radius:0 0 10px 10px; padding:20px !important;
}

/* ── Record cards ── */
.record-card {
    background:#111318; border:1px solid #22262f; border-radius:12px;
    padding:20px 22px 20px 26px; margin-bottom:14px; position:relative; overflow:hidden;
}
.record-card::before {
    content:''; position:absolute; left:0; top:0; bottom:0; width:3px;
    background:linear-gradient(180deg,#2a5cff,#00d97e); border-radius:3px 0 0 3px;
}
.record-name { font-family:'Syne',sans-serif; font-size:17px; font-weight:700; color:#e8ecf4; }
.record-meta { font-family:'JetBrains Mono',monospace; font-size:11px; color:#4d7cff; margin-top:2px; }
.record-id-badge { background:rgba(42,92,255,0.12); border:1px solid rgba(42,92,255,0.3); color:#4d7cff; font-family:'JetBrains Mono',monospace; font-size:11px; padding:3px 10px; border-radius:20px; display:inline-block; }
.field-chip { background:#0a0c10; border:1px solid #22262f; border-radius:8px; padding:9px 12px; margin:4px; display:inline-block; min-width:160px; vertical-align:top; }
.field-label { font-family:'JetBrains Mono',monospace; font-size:9px; color:#484f58; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; }
.field-value { font-family:'JetBrains Mono',monospace; font-size:12px; color:#e8ecf4; word-break:break-all; }
.field-value.null  { color:#484f58; font-style:italic; }
.field-value.true  { color:#00d97e; }
.field-value.false { color:#ff4d6a; }
.field-value.num   { color:#ffa657; }
.section-label { font-family:'JetBrains Mono',monospace; font-size:10px; color:#4d7cff; text-transform:uppercase; letter-spacing:2px; border-bottom:1px solid #22262f; padding-bottom:6px; margin:14px 0 10px; }
.nested-obj { background:#0a0c10; border:1px solid #22262f; border-radius:8px; padding:10px 12px; margin-top:8px; }

/* ── Code blocks ── */
[data-testid="stCode"] { background:#0a0c10 !important; border:1px solid #22262f !important; border-radius:10px !important; }
[data-testid="stCode"] pre { background:transparent !important; font-family:'JetBrains Mono',monospace !important; font-size:12px !important; }

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    background:#111318 !important; color:#00d97e !important;
    border:1px solid #00d97e55 !important; border-radius:8px !important;
    font-family:'JetBrains Mono',monospace !important; font-size:12px !important;
}
[data-testid="stDownloadButton"] > button:hover { background:#00d97e18 !important; }

hr { border-color:#22262f !important; }
.empty-state { text-align:center; padding:70px 20px; font-family:'JetBrains Mono',monospace; color:#484f58; }
.empty-icon  { font-size:48px; margin-bottom:16px; opacity:0.3; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_curl_html(base_url, model, ids, token, provider_key, connection_id):
    masked = (token[:8] + "••••••") if len(token) > 8 else "••••••"
    url_str = f"{base_url}?model={model}&ids={ids}"
    return (
        f'<span class="kw">curl</span> <span class="flag">-v</span> '
        f'<span class="url">"{url_str}"</span> \\\n'
        f'  <span class="flag">-H</span> <span class="val">"Authorization: Bearer {masked}"</span> \\\n'
        f'  <span class="flag">-H</span> <span class="val">"Provider-Config-Key: {provider_key}"</span> \\\n'
        f'  <span class="flag">-H</span> <span class="val">"Connection-Id: {connection_id}"</span>'
    )


def build_curl_plain(base_url, model, ids, token, provider_key, connection_id):
    masked = (token[:8] + "••••••") if len(token) > 8 else "••••••"
    return (
        f'curl -v "{base_url}?model={model}&ids={ids}" \\\n'
        f'  -H "Authorization: Bearer {masked}" \\\n'
        f'  -H "Provider-Config-Key: {provider_key}" \\\n'
        f'  -H "Connection-Id: {connection_id}"'
    )


def colorize_value(val):
    if val is None:
        return '<span class="field-value null">null</span>'
    if isinstance(val, bool):
        css = "true" if val else "false"
        return f'<span class="field-value {css}">{str(val).lower()}</span>'
    if isinstance(val, (int, float)):
        return f'<span class="field-value num">{val}</span>'
    return f'<span class="field-value">{val}</span>'


def render_record_card(rec: dict, index: int) -> str:
    first  = rec.get("legalFirstName", "")
    last   = rec.get("legalLastName", "")
    pref   = rec.get("preferredName", "")
    name   = pref or f"{first} {last}".strip() or rec.get("fullName", "") or f"Record {index+1}"
    emp_id = rec.get("employeeId", rec.get("id", rec.get("_nango_id", f"#{index+1}")))
    job    = rec.get("jobTitle", rec.get("positionTitle", ""))
    dept   = rec.get("department", rec.get("organizationName", ""))
    subtitle = " · ".join(x for x in [job, dept] if x) or "StandardEmployee"

    SKIP = {"legalFirstName","legalLastName","preferredName","fullName","jobTitle","positionTitle"}
    scalar_html = ""
    nested_sections = ""

    for k, v in rec.items():
        if k in SKIP:
            continue
        if isinstance(v, dict):
            inner = "".join(
                f'<div class="field-chip"><div class="field-label">{nk}</div>{colorize_value(nv)}</div>'
                for nk, nv in v.items()
            )
            nested_sections += f'<div class="nested-obj"><div class="section-label">{k}</div><div>{inner}</div></div>'
        elif isinstance(v, list):
            display = json.dumps(v)[:120] + ("…" if len(json.dumps(v)) > 120 else "")
            scalar_html += f'<div class="field-chip"><div class="field-label">{k}</div><span class="field-value">{display}</span></div>'
        else:
            scalar_html += f'<div class="field-chip"><div class="field-label">{k}</div>{colorize_value(v)}</div>'

    return f"""
<div class="record-card">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;
              margin-bottom:14px;border-bottom:1px solid #22262f;padding-bottom:12px">
    <div>
      <div class="record-name">{name}</div>
      <div class="record-meta">{subtitle}</div>
    </div>
    <div class="record-id-badge">#{emp_id}</div>
  </div>
  <div>{scalar_html}</div>
  {nested_sections}
</div>"""


def fetch_records(base_url, model, ids_str, token, provider_key, connection_id):
    url = f"{base_url}?model={model}&ids={ids_str}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Provider-Config-Key": provider_key,
        "Connection-Id": connection_id,
        "Accept": "application/json",
    }
    t0 = time.time()
    resp = requests.get(url, headers=headers, timeout=30)
    elapsed = round((time.time() - t0) * 1000)
    return resp, elapsed


# ── Sidebar — config only ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 20px">
      <div style="font-family:'Syne',sans-serif;font-size:20px;font-weight:800;color:#e8ecf4">
        ⚡ Nango Explorer
      </div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#4d7cff;margin-top:4px;letter-spacing:1px">
        StandardEmployee API
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:#4d7cff;letter-spacing:2px;text-transform:uppercase">🔧 Endpoint</p>', unsafe_allow_html=True)
    base_url      = st.text_input("Base URL", value="https://nango.sandbox-us.laudio.io/records", key="base_url")
    model         = st.text_input("Model",    value="StandardEmployee", key="model")

    st.divider()
    st.markdown('<p style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:#4d7cff;letter-spacing:2px;text-transform:uppercase">🔑 Auth & Headers</p>', unsafe_allow_html=True)
    token         = st.text_input("Bearer Token", value="", type="password", placeholder="Paste token here…", key="token")
    provider_key  = st.text_input("Provider-Config-Key", value="workday", key="pck")
    connection_id = st.text_input("Connection-Id", value="3-nmht-sandbox", key="cid")

    st.divider()
    st.markdown('<p style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:#4d7cff;letter-spacing:2px;text-transform:uppercase">🔍 Query</p>', unsafe_allow_html=True)
    ids_input = st.text_input(
        "Employee ID(s) — comma-separated",
        value="05640",
        placeholder="e.g. 05640, 05641",
        key="ids",
        help="Enter one or more employee IDs separated by commas"
    )
    fetch_clicked = st.button("⚡  Fetch Records", use_container_width=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "last_response" not in st.session_state:
    st.session_state.last_response = None

ids_clean = ",".join(i.strip() for i in ids_input.split(",") if i.strip())

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-row">
    <div class="hero-logo">N↗</div>
    <div>
      <div class="hero-title">Nango API Explorer</div>
      <div class="hero-sub">StandardEmployee · Laudio Sandbox · workday integration</div>
    </div>
    <div class="hero-dot"><div class="live-dot"></div>sandbox-us</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Two-column layout: config summary (left) | cURL (right) ───────────────────
col_left, col_right = st.columns([1, 1], gap="medium")

with col_left:
    cfg_rows = [
        ("URL",           f"{base_url}?model={model}&ids={ids_clean or '…'}"),
        ("Provider-Key",  provider_key),
        ("Connection-Id", connection_id),
        ("Auth",          "Bearer ••••••" if token else "⚠ No token set"),
        ("IDs",           ids_clean or "—"),
    ]
    rows_html = "".join(
        f'<div style="display:flex;gap:12px;padding:9px 0;border-bottom:1px solid #22262f;'
        f'font-family:\'JetBrains Mono\',monospace;font-size:12px">'
        f'<div style="min-width:110px;color:#484f58;font-size:10px;text-transform:uppercase;'
        f'letter-spacing:1px;padding-top:2px">{label}</div>'
        f'<div style="color:#e8ecf4;word-break:break-all">{value}</div></div>'
        for label, value in cfg_rows
    )
    st.markdown(f"""
    <div class="panel-card">
      <div class="panel-label">Endpoint Config</div>
      {rows_html}
    </div>
    """, unsafe_allow_html=True)

with col_right:
    curl_html = build_curl_html(
        base_url, model,
        ids_clean or "…",
        token or "&lt;TOKEN&gt;",
        provider_key, connection_id
    )
    st.markdown(f"""
    <div class="curl-panel">
      <div class="curl-header">⌨ cURL Command</div>
      <div class="curl-box">{curl_html}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#484f58;margin-top:10px">
        ↑ Updates live as you edit fields in the sidebar
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ── Fetch ─────────────────────────────────────────────────────────────────────
if fetch_clicked:
    if not ids_clean:
        st.error("Please enter at least one Employee ID.")
    elif not token:
        st.error("Bearer token is required.")
    else:
        with st.spinner("Fetching records from Nango…"):
            try:
                resp, elapsed = fetch_records(base_url, model, ids_clean, token, provider_key, connection_id)
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text

                st.session_state.last_response = {
                    "status_code": resp.status_code,
                    "ok": resp.ok,
                    "elapsed": elapsed,
                    "data": data,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "ids": ids_clean,
                    "url": f"{base_url}?model={model}&ids={ids_clean}",
                }
            except requests.exceptions.ConnectionError:
                st.error("❌ Connection failed — check the base URL and your network.")
            except requests.exceptions.Timeout:
                st.error("⏱ Request timed out after 30 seconds.")
            except Exception as e:
                st.error(f"Unexpected error: {e}")


# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.last_response:
    r    = st.session_state.last_response
    data = r["data"]
    ok   = r["ok"]

    badge_cls = "badge-ok" if ok else "badge-err"
    badge_txt = f"✓ {r['status_code']} OK" if ok else f"✗ {r['status_code']}"

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-box">
        <div class="metric-title">Status</div>
        <div style="margin-top:6px"><span class="badge {badge_cls}">{badge_txt}</span></div>
      </div>
      <div class="metric-box">
        <div class="metric-title">Latency</div>
        <div class="metric-val">{r['elapsed']} ms</div>
      </div>
      <div class="metric-box">
        <div class="metric-title">Time</div>
        <div class="metric-val" style="font-size:14px">{r['timestamp']}</div>
      </div>
      <div class="metric-box">
        <div class="metric-title">IDs Queried</div>
        <div class="metric-val" style="font-size:14px">{r['ids']}</div>
      </div>
    </div>
    <div class="url-bar">
      GET &nbsp;<span style="color:#4d7cff">{r['url']}</span>
    </div>
    """, unsafe_allow_html=True)

    tab_raw, tab_beautiful, tab_info = st.tabs(["⬚  Raw JSON", "✦  Beautiful View", "📋  Response Info"])

    with tab_raw:
        json_str = json.dumps(data, indent=2) if not isinstance(data, str) else data
        if isinstance(data, list):
            st.markdown(f'<span class="badge badge-ok" style="margin-bottom:10px;display:inline-block">{len(data)} record(s)</span>', unsafe_allow_html=True)
        elif isinstance(data, dict) and "records" in data:
            st.markdown(f'<span class="badge badge-ok" style="margin-bottom:10px;display:inline-block">{len(data["records"])} record(s)</span>', unsafe_allow_html=True)
        st.code(json_str, language="json")
        st.download_button(
            label="⬇  Download JSON",
            data=json_str,
            file_name=f"nango_{r['ids']}_{r['timestamp'].replace(':','')}.json",
            mime="application/json",
        )

    with tab_beautiful:
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict) and "records" in data and isinstance(data["records"], list):
            records = data["records"]
        elif isinstance(data, dict) and ok:
            records = [data]
        else:
            records = None

        if not ok:
            st.markdown("""
            <div style="background:#ff4d6a18;border:1px solid #ff4d6a55;border-radius:10px;
                        padding:18px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#ff4d6a">
              ⚠ API returned an error — check the Raw JSON tab for details.
            </div>""", unsafe_allow_html=True)
        elif not records:
            st.markdown('<div style="text-align:center;padding:40px;font-family:\'JetBrains Mono\',monospace;color:#484f58">No records returned.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="badge badge-ok" style="margin-bottom:14px;display:inline-block">{len(records)} employee record(s)</span>', unsafe_allow_html=True)
            for i, rec in enumerate(records):
                st.markdown(render_record_card(rec, i), unsafe_allow_html=True)

    with tab_info:
        st.markdown('<div class="section-label">Request Details</div>', unsafe_allow_html=True)
        st.code(f"""URL:              {r['url']}
Method:           GET
Provider-Key:     {provider_key}
Connection-Id:    {connection_id}
Timestamp:        {r['timestamp']}
Latency:          {r['elapsed']} ms
Status:           {r['status_code']}""", language="yaml")

        st.markdown('<div class="section-label" style="margin-top:16px">Full cURL (token masked)</div>', unsafe_allow_html=True)
        st.code(build_curl_plain(base_url, model, r["ids"], token, provider_key, connection_id), language="bash")

else:
    st.markdown("""
    <div class="empty-state">
      <div class="empty-icon">⬡</div>
      <div style="font-size:14px">Configure your request in the sidebar and hit
        <strong style="color:#2a5cff">⚡ Fetch Records</strong>
      </div>
      <div style="font-size:11px;margin-top:8px;color:#30363d">Supports multiple comma-separated IDs</div>
    </div>
    """, unsafe_allow_html=True)
