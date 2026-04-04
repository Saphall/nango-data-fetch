# Nango API Explorer

A Streamlit web app to query the Nango StandardEmployee API interactively.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Then open <http://localhost:8501> in your browser.


![Nango API Explorer Demo](./assets/demo.png)


## Features

- **Sidebar config** — Base URL, Model, Bearer token (masked), Provider-Config-Key, Connection-Id
- **Multi-ID support** — enter comma-separated employee IDs
- **Live cURL preview** — see the exact curl command in the sidebar
- **Raw JSON tab** — syntax-highlighted with download button
- **Beautiful View tab** — renders each employee as a structured card
- **Response Info tab** — status, latency, request metadata
