"""
Renders a self-contained, searchable HTML page of all saved tools. Served live
by the Render web service (web.py), so it always reflects the current Gist.

Everything (CSS + JS) is inlined so it works with no external assets. The tool
data is embedded as JSON and filtered client-side by search box + category.
"""

import json
from datetime import datetime, timezone

import saved_tools


def _page(data: dict) -> str:
    total = sum(len(v) for v in data.values())
    cats = sorted(((c, len(v)) for c, v in data.items() if v), key=lambda x: (-x[1], x[0]))
    generated = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    # Embed data safely inside a <script> tag.
    payload = json.dumps(data).replace("</", "<\\/")

    chips = '<button class="chip active" data-cat="">All ({})</button>'.format(total)
    chips += "".join(
        f'<button class="chip" data-cat="{c}">{c} ({n})</button>' for c, n in cats
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>My AI Tools</title>
<style>
  :root {{
    --bg:#f6f7f9; --card:#fff; --text:#14181f; --muted:#6b7280;
    --border:#e5e7eb; --accent:#2563eb; --chip:#eef2ff; --chip-text:#3730a3;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg:#0f1216; --card:#171b21; --text:#e6e9ee; --muted:#9aa4b2;
      --border:#262c36; --accent:#5b9dff; --chip:#1e2530; --chip-text:#a9c4ff;
    }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
    font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
  header {{ padding:28px 20px 8px; max-width:900px; margin:0 auto; }}
  h1 {{ margin:0 0 4px; font-size:1.6rem; letter-spacing:-.02em; }}
  .sub {{ color:var(--muted); font-size:.9rem; }}
  .wrap {{ max-width:900px; margin:0 auto; padding:0 20px 60px; }}
  .search {{ width:100%; padding:12px 14px; margin:16px 0 12px; font-size:1rem;
    border:1px solid var(--border); border-radius:12px; background:var(--card); color:var(--text); }}
  .search:focus {{ outline:2px solid var(--accent); border-color:transparent; }}
  .chips {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:18px; }}
  .chip {{ border:1px solid var(--border); background:var(--card); color:var(--text);
    padding:6px 12px; border-radius:999px; font-size:.82rem; cursor:pointer; }}
  .chip.active {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:14px; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:14px;
    padding:16px; display:flex; flex-direction:column; gap:8px; }}
  .card a.title {{ font-weight:600; color:var(--text); text-decoration:none; font-size:1.02rem; }}
  .card a.title:hover {{ color:var(--accent); text-decoration:underline; }}
  .badge {{ align-self:flex-start; background:var(--chip); color:var(--chip-text);
    font-size:.72rem; padding:3px 9px; border-radius:999px; }}
  .summary {{ color:var(--muted); font-size:.9rem; margin:0; }}
  .src {{ color:var(--muted); font-size:.75rem; }}
  .empty {{ color:var(--muted); text-align:center; padding:50px 0; }}
</style>
</head>
<body>
<header>
  <h1>🧰 My AI Tools</h1>
  <div class="sub">{total} saved · updated {generated}</div>
</header>
<div class="wrap">
  <input id="q" class="search" type="search" placeholder="Search tools by name, topic, or keyword…">
  <div class="chips" id="chips">{chips}</div>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" style="display:none">No tools match your search.</div>
</div>
<script>
  const DATA = {payload};
  const flat = [];
  for (const [cat, items] of Object.entries(DATA))
    for (const it of items) flat.push({{...it, cat}});
  flat.sort((a,b)=> (b.saved_at||"").localeCompare(a.saved_at||""));

  const grid = document.getElementById('grid');
  const empty = document.getElementById('empty');
  const q = document.getElementById('q');
  let activeCat = "";

  const esc = s => (s||"").replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));

  function render() {{
    const term = q.value.trim().toLowerCase();
    const rows = flat.filter(it => {{
      if (activeCat && it.cat !== activeCat) return false;
      if (!term) return true;
      return (it.title+" "+it.summary+" "+it.cat).toLowerCase().includes(term);
    }});
    empty.style.display = rows.length ? 'none' : 'block';
    grid.innerHTML = rows.map(it => `
      <div class="card">
        <span class="badge">${{esc(it.cat)}}</span>
        <a class="title" href="${{esc(it.url)}}" target="_blank" rel="noopener">${{esc(it.title)}}</a>
        <p class="summary">${{esc(it.summary)}}</p>
        ${{it.source ? `<span class="src">${{esc(it.source)}}</span>` : ""}}
      </div>`).join("");
  }}

  document.getElementById('chips').addEventListener('click', e => {{
    if (!e.target.classList.contains('chip')) return;
    activeCat = e.target.dataset.cat;
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    e.target.classList.add('active');
    render();
  }});
  q.addEventListener('input', render);
  render();
</script>
</body>
</html>"""


def render() -> bytes:
    return _page(saved_tools.all_tools()).encode("utf-8")
