import streamlit as st
import truststore
import requests
import html
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse

import pandas as pd
from dotenv import dotenv_values, set_key, unset_key

# Use the OS trust store (as curl does) so internal/corporate CAs are accepted
truststore.inject_into_ssl()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nango API Explorer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
STYLES = (Path(__file__).parent / "ui.css").read_text()
THEMES = {
    # Ink background, teal primary, amber highlight
    "dark": {
        "bg": "#0a0f16", "blob-1": "rgba(20,184,166,.36)", "blob-2": "rgba(251,191,36,.14)", "blob-3": "rgba(99,102,241,.30)",
        "glass": "rgba(255,255,255,.055)", "glass-strong": "rgba(255,255,255,.09)", "highlight": "rgba(255,255,255,.10)",
        "border": "rgba(255,255,255,.12)", "text": "#e9eef5", "muted": "#9ba7b8", "dim": "#6c7889",
        "accent": "#2dd4bf", "accent-soft": "rgba(45,212,191,.20)", "ok": "#34d399", "danger": "#fb7185",
        "c-kw": "#fbbf24", "grad": "linear-gradient(135deg,#2dd4bf,#38bdf8)", "on-accent": "#04211f",
        "input-bg": "rgba(255,255,255,.06)", "chip-bg": "rgba(255,255,255,.05)", "code-bg": "rgba(0,0,0,.30)",
        "sidebar-bg": "rgba(9,13,20,.66)", "pop-bg": "#141c28", "shadow": "0 8px 32px rgba(0,0,0,.38)", "invert": "none",
    },
    # Warm paper background
    "light": {
        "bg": "#f5f1e9", "blob-1": "rgba(20,184,166,.26)", "blob-2": "rgba(251,146,60,.24)", "blob-3": "rgba(129,140,248,.24)",
        "glass": "rgba(255,255,255,.58)", "glass-strong": "rgba(255,255,255,.80)", "highlight": "rgba(255,255,255,.95)",
        "border": "rgba(40,50,60,.12)", "text": "#17202a", "muted": "#4a5565", "dim": "#7a8494",
        "accent": "#0f766e", "accent-soft": "rgba(15,118,110,.15)", "ok": "#15803d", "danger": "#be123c",
        "c-kw": "#b45309", "grad": "linear-gradient(135deg,#0f766e,#0369a1)", "on-accent": "#ffffff",
        "input-bg": "rgba(255,255,255,.78)", "chip-bg": "rgba(255,255,255,.65)", "code-bg": "rgba(255,255,255,.66)",
        "sidebar-bg": "rgba(250,247,240,.70)", "pop-bg": "#ffffff", "shadow": "0 8px 30px rgba(60,50,30,.12)",
        "invert": "invert(1) hue-rotate(180deg)",
    },
}


def apply_theme(mode):
    variables = "".join(f"--{k}:{v};" for k, v in THEMES[mode].items())
    st.markdown(f"<style>{STYLES}\n:root{{{variables}}}</style>", unsafe_allow_html=True)


apply_theme("light" if st.session_state.get("light_mode") else "dark")


# ── Helpers ───────────────────────────────────────────────────────────────────

ENV_PATH = Path(__file__).parent / ".env"
DEFAULT_BASE_URL = "https://nango.{env}.laudio.io/records"
ENVIRONMENTS = ["sandbox-global", "sandbox-us", "dev", "stg", "prod"]
CLIENT_KEY_RE = re.compile(r"^([A-Z0-9]+)_NANGO_CONNECTION_ID$")
PROVIDER_KEYS = ["workday", "workday-oauth", "ukg-pro", "ukg-pro-wfm", "sharepoint-online-oauth2-cc"]
CUSTOM_MODEL = "✏️ Custom…"
CUSTOM_PROVIDER = "✏️ Custom…"
CUSTOM_CLIENT = "✏️ Custom…"
RAW_PREVIEW_CHARS = 60_000
MAX_VALUE_CHARS = 300

# model -> Nango sync that produces it
MODELS = {
    "Company": "companies",
    "CostCenter": "cost-centers",
    "Location": "locations",
    "MatrixRelationship": "matrix-managers",
    "PtoBalance": "pto-balance",
    "LicenseRaas": "raas-license",
    "EmployeeRaas": "raas-unified-employees",
    "StandardAbsence": "timesheet-absence",
    "StandardSchedule": "timesheet-schedule",
    "StandardTimesheet": "time-tracking",
    "StandardEmployee": "unified-employees",
}


def esc(value):
    return html.escape(str(value))


def load_env():
    values = {k: v for k, v in dotenv_values(ENV_PATH).items() if v is not None}
    values.update({k: v for k, v in os.environ.items() if "_NANGO_" in k})
    return values


def env_key(prefix, field):
    """e.g. ('sandbox-global', 'BASE_URL') -> SANDBOX_GLOBAL_NANGO_BASE_URL"""
    return f"{prefix.strip().upper().replace('-', '_')}_NANGO_{field}"


def discover_clients(env):
    """Clients are the <CLIENT> prefixes of <CLIENT>_NANGO_CONNECTION_ID entries, in .env order."""
    return list(dict.fromkeys(m.group(1).lower() for k in env if (m := CLIENT_KEY_RE.match(k))))


def build_params(model, ids, limit, cursor=None):
    params = {"model": model}
    if ids:
        params["ids"] = ids
    if limit:
        params["limit"] = limit
    if cursor:
        params["cursor"] = cursor
    return params


def build_url(base_url, params):
    return f"{base_url}?{urlencode(params, safe=',')}"


def mask_token(token):
    return f"{token[:4]}••••••" if token else "<TOKEN>"


def build_curl_plain(url, token, provider_key, connection_id, reveal=False):
    shown = token if (reveal and token) else mask_token(token)
    return (
        f'curl -v "{url}" \\\n'
        f'  -H "Authorization: Bearer {shown}" \\\n'
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
    text = val if isinstance(val, str) else json.dumps(val)
    if len(text) > MAX_VALUE_CHARS:
        text = text[:MAX_VALUE_CHARS] + "…"
    return f'<span class="field-value">{esc(text)}</span>'


def extract_records(data, ok):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("records"), list):
            return data["records"]
        if ok:
            return [data]
    return None


def records_to_df(records):
    df = pd.json_normalize([r for r in records if isinstance(r, dict)], sep=".")
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, (list, dict))).any():
            df[col] = df[col].map(lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v)
    return df


def render_record_card(rec, index: int, model: str) -> str:
    if not isinstance(rec, dict):
        rec = {"value": rec}

    def _subtitle_part(value):
        if value in (None, ""):
            return ""
        if isinstance(value, dict):
            for key in ("name", "title", "displayName", "value", "id"):
                candidate = value.get(key)
                if candidate not in (None, ""):
                    return str(candidate)
            return json.dumps(value, ensure_ascii=True)
        if isinstance(value, list):
            return ", ".join(str(item) for item in value if item not in (None, ""))
        return str(value)

    first = rec.get("legalFirstName") or rec.get("firstName") or ""
    last  = rec.get("legalLastName") or rec.get("lastName") or ""
    name_keys = ("preferredName", "displayName", "fullName", "name", "departmentName", "title", "description")
    name = (
        rec.get("preferredName")
        or f"{first} {last}".strip()
        or next((_subtitle_part(rec[k]) for k in name_keys if rec.get(k)), "")
        or f"Record {index+1}"
    )
    rec_id = rec.get("employeeId", rec.get("id", rec.get("_nango_id", f"{index+1}")))
    job    = rec.get("jobTitle", rec.get("positionTitle", ""))
    dept   = rec.get("department", rec.get("organizationName", ""))
    subtitle = " · ".join(x for x in (_subtitle_part(job), _subtitle_part(dept)) if x) or model

    SKIP = {"legalFirstName", "legalLastName", "preferredName", "fullName", "jobTitle", "positionTitle"}
    scalar_html = ""
    nested_sections = ""

    for k, v in rec.items():
        if k in SKIP:
            continue
        if isinstance(v, dict):
            inner = "".join(
                f'<div class="field-chip"><div class="field-label">{esc(nk)}</div>{colorize_value(nv)}</div>'
                for nk, nv in v.items()
            )
            nested_sections += (
                f'<div class="nested-obj"><div class="section-label">{esc(k)}</div>'
                f'<div class="card-scroll">{inner}</div></div>'
            )
        else:
            scalar_html += f'<div class="field-chip"><div class="field-label">{esc(k)}</div>{colorize_value(v)}</div>'

    return f"""
<div class="record-card">
  <div class="record-head">
    <div>
      <div class="record-name">{esc(name)}</div>
      <div class="record-meta">{esc(subtitle)}</div>
    </div>
    <div class="record-id-badge">#{esc(rec_id)}</div>
  </div>
  <div>{scalar_html}</div>
  {nested_sections}
</div>"""


def do_fetch(req, page=1):
    """Run the request and store the outcome in session state."""
    st.session_state.fetch_error = None
    url = build_url(req["base_url"], req["params"])
    headers = {
        "Authorization": f"Bearer {req['token']}",
        "Provider-Config-Key": req["provider_key"],
        "Connection-Id": req["connection_id"],
        "Accept": "application/json",
    }
    try:
        t0 = time.time()
        resp = requests.get(url, headers=headers, timeout=60)
        elapsed = round((time.time() - t0) * 1000)
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        st.session_state.last_response = {
            "status_code": resp.status_code,
            "ok": resp.ok,
            "elapsed": elapsed,
            "data": data,
            "size": len(resp.content),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "model": req["params"]["model"],
            "page": page,
            "next_cursor": data.get("next_cursor") if isinstance(data, dict) else None,
            "url": url,
            "req": req,
        }
    except requests.exceptions.SSLError as e:
        st.session_state.fetch_error = f"🔒 SSL certificate error: {e}"
    except requests.exceptions.ConnectionError:
        st.session_state.fetch_error = "❌ Connection failed — check the base URL and your network."
    except requests.exceptions.Timeout:
        st.session_state.fetch_error = "⏱ Request timed out after 60 seconds."
    except Exception as e:
        st.session_state.fetch_error = f"Unexpected error: {e}"


def go_next_page():
    r = st.session_state.last_response
    req = {**r["req"], "params": {**r["req"]["params"], "cursor": r["next_cursor"]}}
    do_fetch(req, page=r["page"] + 1)


def human_size(n):
    return f"{n/1024:.1f} KB" if n < 1024 * 1024 else f"{n/1024/1024:.2f} MB"


# ── Sidebar — config only ─────────────────────────────────────────────────────
def sidebar_heading(num, text):
    st.markdown(f'<div class="side-heading"><span class="side-num">{num}</span>{text}</div>', unsafe_allow_html=True)


env = load_env()

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <div class="brand-logo">N</div>
      <div>
        <div class="brand-name">Nango Explorer</div>
        <div class="brand-tag">Browse synced records</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.toggle("Light mode", key="light_mode")
    st.divider()

    sidebar_heading(1, "Connection")
    environment = st.selectbox("Environment", ENVIRONMENTS, key="environment")

    clients = discover_clients(env)
    client_choice = st.selectbox("Client", [*clients, CUSTOM_CLIENT], key="client_choice")
    if client_choice == CUSTOM_CLIENT:
        client = st.text_input("Custom client", key="custom_client", placeholder="e.g. gei1").strip().lower()
    else:
        client = client_choice

    # Widget keys include the environment/client so each keeps its own editable values.
    connection_id = st.text_input(
        "Connection-Id", value=env.get(env_key(client, "CONNECTION_ID"), "") if client else "", key=f"cid::{client}"
    )
    pck_default = (env.get(env_key(client, "PROVIDER_CONFIG_KEY"), "") if client else "") or PROVIDER_KEYS[0]
    pck_options = [*PROVIDER_KEYS, *([pck_default] if pck_default not in PROVIDER_KEYS else []), CUSTOM_PROVIDER]
    pck_choice = st.selectbox("Provider-Config-Key", pck_options, index=pck_options.index(pck_default), key=f"pck::{client}")
    if pck_choice == CUSTOM_PROVIDER:
        provider_key = st.text_input("Custom provider key", key=f"pck_custom::{client}", placeholder="e.g. workday-oauth").strip()
    else:
        provider_key = pck_choice

    tok_val = env.get(env_key(environment, "BEARER_TOKEN"), "")
    token = st.text_input("Bearer token", value=tok_val, type="password",
                          placeholder="Paste token here…", key=f"token::{environment}")
    if not tok_val:
        st.markdown(
            f'<div class="src-note"><b class="warn">No token for {esc(environment)} in .env</b> — paste one above</div>',
            unsafe_allow_html=True,
        )

    with st.expander("Advanced · base URL"):
        base_url = st.text_input(
            "Base URL",
            value=env.get(env_key(environment, "BASE_URL"), DEFAULT_BASE_URL.format(env=environment)),
            key=f"base_url::{environment}",
        )

    if st.button("💾  Save to .env", width="stretch", disabled=not client, key="save_env",
                 help=f"Saves {env_key(environment, '*')} (base URL, token) and {env_key(client or 'client', '*')} "
                      "(connection id, provider key)."):
        ENV_PATH.touch(exist_ok=True)
        set_key(ENV_PATH, env_key(environment, "BASE_URL"), base_url)
        set_key(ENV_PATH, env_key(environment, "BEARER_TOKEN"), token)
        set_key(ENV_PATH, env_key(client, "CONNECTION_ID"), connection_id)
        set_key(ENV_PATH, env_key(client, "PROVIDER_CONFIG_KEY"), provider_key)
        st.toast(f"Saved {environment} / {client} settings to .env", icon="✅")

    st.divider()
    sidebar_heading(2, "Request")
    model_choice = st.selectbox(
        "Model",
        [*MODELS, CUSTOM_MODEL],
        index=list(MODELS).index("StandardEmployee"),
        format_func=lambda m: m if m == CUSTOM_MODEL else f"{m}  ·  {MODELS[m]}",
        key="model_choice",
    )
    if model_choice == CUSTOM_MODEL:
        model = st.text_input("Custom model name", key="custom_model", placeholder="e.g. Company").strip()
    else:
        model = model_choice
    ids_input = st.text_input(
        "Record IDs (optional)",
        value="",
        placeholder="Leave empty to fetch all",
        key="ids",
        help="Comma-separated record IDs. Not needed for most models.",
    )
    limit = st.number_input(
        "Page size", min_value=1, max_value=1000, value=100, step=50, key="limit",
        help="Records per request (limit). Use 'Next page' in the results to continue.",
    )


# ── Session state ─────────────────────────────────────────────────────────────
st.session_state.setdefault("last_response", None)
st.session_state.setdefault("fetch_error", None)

ids_clean = ",".join(i.strip() for i in ids_input.split(",") if i.strip())
preview_url = build_url(base_url, build_params(model or "…", ids_clean, limit))

# ── Hero ──────────────────────────────────────────────────────────────────────
ENV_COLORS = {"prod": "var(--danger)", "stg": "var(--c-kw)", "dev": "var(--c-kw)"}


def ctx_chip(label, value, color="var(--accent)", warn=False):
    return (
        f'<div class="ctx-chip{" warn" if warn else ""}"><span class="ctx-dot" style="background:{color}"></span>'
        f'<span class="ctx-k">{label}</span><span class="ctx-v">{esc(value)}</span></div>'
    )


st.markdown(f"""
<div class="hero">
  <div>
    <div class="hero-title">Nango API Explorer</div>
    <div class="hero-sub">Fetch and inspect synced records from any model.</div>
  </div>
  <div class="host-pill"><span class="live-dot"></span>{esc(urlparse(base_url).hostname or base_url)}</div>
</div>
<div class="ctx-row">
  {ctx_chip("Environment", environment, ENV_COLORS.get(environment, "var(--accent)"))}
  {ctx_chip("Client", client or "not set", warn=not client)}
  {ctx_chip("Model", model or "not set", warn=not model)}
  {ctx_chip("Provider", provider_key or "not set", warn=not provider_key)}
  {ctx_chip("Token", "set" if token else "missing", "var(--ok)" if token else "var(--danger)", warn=not token)}
</div>
""", unsafe_allow_html=True)

# ── Request bar ───────────────────────────────────────────────────────────────
url_base, _, url_query = preview_url.partition("?")
bar_col, send_col = st.columns([6, 1], vertical_alignment="center")
with bar_col:
    st.markdown(
        f'<div class="reqbar"><span class="method">GET</span>'
        f'<span class="url-text">{esc(url_base)}<span class="q">?{esc(url_query)}</span></span></div>',
        unsafe_allow_html=True,
    )
with send_col:
    fetch_clicked = st.button("Send  ▶", type="primary", width="stretch", key="send")

with st.expander("cURL command"):
    reveal = st.toggle("Reveal token so the command can be copied and run", key="reveal_token")
    st.code(build_curl_plain(preview_url, token, provider_key, connection_id, reveal=reveal), language="bash")

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ── Fetch ─────────────────────────────────────────────────────────────────────
if fetch_clicked:
    if not model:
        st.error("Please choose or enter a model.")
    elif not token:
        st.error("Bearer token is required.")
    else:
        with st.spinner("Fetching records from Nango…"):
            do_fetch({
                "base_url": base_url,
                "params": build_params(model, ids_clean, limit),
                "token": token,
                "provider_key": provider_key,
                "connection_id": connection_id,
            })

if st.session_state.fetch_error:
    st.error(st.session_state.fetch_error)


# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.last_response:
    r    = st.session_state.last_response
    data = r["data"]
    ok   = r["ok"]
    all_records = extract_records(data, ok)

    badge_cls = "badge-ok" if ok else "badge-err"
    badge_txt = f"✓ {r['status_code']} OK" if ok else f"✗ {r['status_code']}"
    count_txt = f"{len(all_records):,}" if all_records is not None else "—"

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-box">
        <div class="metric-title">Status</div>
        <div style="margin-top:6px"><span class="badge {badge_cls}">{badge_txt}</span></div>
      </div>
      <div class="metric-box">
        <div class="metric-title">Model</div>
        <div style="margin-top:6px"><span class="model-pill">{esc(r['model'])}</span></div>
      </div>
      <div class="metric-box">
        <div class="metric-title">Records (page {r['page']})</div>
        <div class="metric-val">{count_txt}</div>
      </div>
      <div class="metric-box">
        <div class="metric-title">Size</div>
        <div class="metric-val" style="font-size:14px">{human_size(r['size'])}</div>
      </div>
      <div class="metric-box">
        <div class="metric-title">Latency</div>
        <div class="metric-val" style="font-size:14px">{r['elapsed']} ms</div>
      </div>
      <div class="metric-box">
        <div class="metric-title">Time</div>
        <div class="metric-val" style="font-size:14px">{r['timestamp']}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    bar_filter, bar_next = st.columns([3, 1], vertical_alignment="bottom")
    with bar_filter:
        needle = st.text_input(
            "Filter records on this page", key="filter",
            placeholder="Type to filter the Table and Cards views…",
        ).strip().lower() if all_records else ""
    with bar_next:
        if r["next_cursor"]:
            st.button("Next page  ▶", key="next_page", on_click=go_next_page, width="stretch")
        elif all_records:
            st.markdown('<div class="src-note" style="margin:0">Last page</div>', unsafe_allow_html=True)

    shown = (
        [rec for rec in all_records if needle in json.dumps(rec).lower()]
        if needle and all_records else all_records
    )

    tab_table, tab_beautiful, tab_raw, tab_info = st.tabs(["Table", "Cards", "Raw JSON", "Response info"])

    with tab_table:
        if not ok:
            st.error("API returned an error — check the Raw JSON tab for details.")
        elif not shown:
            st.markdown('<div class="no-records">No records to show.</div>', unsafe_allow_html=True)
        else:
            st.caption(f"{len(shown):,} of {len(all_records):,} record(s) · nested fields are flattened (a.b.c)")
            st.dataframe(records_to_df(shown), width="stretch", height=520)

    with tab_raw:
        json_str = json.dumps(data, indent=2) if not isinstance(data, str) else data
        if len(json_str) > RAW_PREVIEW_CHARS:
            st.warning(
                f"Large response ({human_size(r['size'])}) — previewing the first {RAW_PREVIEW_CHARS:,} of "
                f"{len(json_str):,} characters. Download for the full payload."
            )
        st.code(json_str[:RAW_PREVIEW_CHARS], language="json")
        st.download_button(
            label="⬇  Download full JSON",
            data=json_str,
            file_name=f"nango_{r['model']}_p{r['page']}_{r['timestamp'].replace(':','')}.json",
            mime="application/json",
        )
        if all_records:
            with st.expander("🌲 Tree view (first 25 records)"):
                st.json(all_records[:25], expanded=1)

    with tab_beautiful:
        if not ok:
            st.error("API returned an error — check the Raw JSON tab for details.")
        elif not shown:
            st.markdown('<div class="no-records">No records to show.</div>', unsafe_allow_html=True)
        else:
            c_size, c_page, c_info = st.columns([1, 1, 3], vertical_alignment="bottom")
            page_size = c_size.selectbox("Cards per view", [10, 25, 50], key="card_page_size")
            n_pages = max(1, -(-len(shown) // page_size))
            view_page = c_page.number_input("View", 1, n_pages, 1, key="card_view_page")
            start = (view_page - 1) * page_size
            c_info.markdown(
                f'<span class="badge badge-ok">{start + 1:,}–{min(start + page_size, len(shown)):,} '
                f'of {len(shown):,} · view {view_page}/{n_pages}</span>',
                unsafe_allow_html=True,
            )
            for i, rec in enumerate(shown[start:start + page_size], start=start):
                st.markdown(render_record_card(rec, i, r["model"]), unsafe_allow_html=True)

    with tab_info:
        req = r["req"]
        st.markdown('<div class="section-label">Request Details</div>', unsafe_allow_html=True)
        st.code(f"""URL:              {r['url']}
Method:           GET
Model:            {r['model']}
Provider-Key:     {req['provider_key']}
Connection-Id:    {req['connection_id']}
Page:             {r['page']}
Next cursor:      {r['next_cursor'] or '—'}
Timestamp:        {r['timestamp']}
Latency:          {r['elapsed']} ms
Size:             {human_size(r['size'])}
Status:           {r['status_code']}""", language="yaml")

        st.markdown('<div class="section-label" style="margin-top:16px">Full cURL (token masked)</div>', unsafe_allow_html=True)
        st.code(build_curl_plain(r["url"], req["token"], req["provider_key"], req["connection_id"]), language="bash")

else:
    st.markdown("""
    <div class="empty-state">
      <div class="empty-title">Ready when you are</div>
      <div class="empty-sub">Three quick steps to pull records from Nango.</div>
      <div class="steps">
        <div class="step"><div class="step-n">1</div><div class="step-t">Connect</div>
          <div class="step-d">Choose an environment and client. Connection, provider and token load from your <span class="mono">.env</span>.</div></div>
        <div class="step"><div class="step-n">2</div><div class="step-t">Pick a model</div>
          <div class="step-d">Select the model to fetch. Record IDs are optional, so leave them empty to get everything.</div></div>
        <div class="step"><div class="step-n">3</div><div class="step-t">Send &amp; explore</div>
          <div class="step-d">Hit Send, then browse as a table, cards or raw JSON. Use Next page for large models.</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)
