import os
import json
import random
import datetime
import calendar
import urllib.request
import urllib.error

GITHUB_TOKEN = os.environ.get("PAT_TOKEN") or os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER  = os.environ.get("GITHUB_USER", "EvaniIdo")

def gh_get(url, use_auth=True):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    if use_auth and GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if use_auth and GITHUB_TOKEN and e.code in (401, 403, 404):
            return gh_get(url, use_auth=False)
        return []
    except Exception:
        return []

def fetch_graphql_contributions(username, year, month):
    if not GITHUB_TOKEN:
        return None
    last_day = calendar.monthrange(year, month)[1]
    from_date = f"{year}-{month:02d}-01T00:00:00Z"
    to_date = f"{year}-{month:02d}-{last_day:02d}T23:59:59Z"

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({
        "query": query,
        "variables": {"login": username, "from": from_date, "to": to_date}
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            days = {}
            weeks = data.get("data", {}).get("user", {}).get("contributionsCollection", {}).get("contributionCalendar", {}).get("weeks", [])
            for w in weeks:
                for d in w.get("contributionDays", []):
                    parts = d["date"].split("-")
                    if int(parts[0]) == year and int(parts[1]) == month:
                        day_num = int(parts[2])
                        days[day_num] = d["contributionCount"]
            return days if days else None
    except Exception:
        return None

def fetch_search_commits(username, year, month, last_day):
    url = f"https://api.github.com/search/commits?q=author:{username}+author-date:{year}-{month:02d}-01..{year}-{month:02d}-{last_day:02d}&per_page=100"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/vnd.github.cloak-preview"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    counts = {}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            items = data.get("items", [])
            for item in items:
                d_str = item.get("commit", {}).get("author", {}).get("date")
                if not d_str:
                    continue
                try:
                    dt = datetime.datetime.fromisoformat(d_str.replace("Z", "+00:00"))
                    local_dt = dt.astimezone(datetime.timezone(datetime.timedelta(hours=-3)))
                    if local_dt.year == year and local_dt.month == month:
                        counts[local_dt.day] = counts.get(local_dt.day, 0) + 1
                except Exception:
                    pass
    except Exception:
        pass
    return counts

def fetch_repos():
    repos, page = [], 1
    while True:
        chunk = gh_get(f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&page={page}&type=owner")
        if not chunk or not isinstance(chunk, list):
            break
        repos += [r["full_name"] for r in chunk if isinstance(r, dict) and "full_name" in r]
        if len(chunk) < 100:
            break
        page += 1
    return repos

def commits_by_day(year, month):
    last_day = calendar.monthrange(year, month)[1]
    counts = {d: 0 for d in range(1, last_day + 1)}

    gql_counts = fetch_graphql_contributions(GITHUB_USER, year, month) or {}
    search_counts = fetch_search_commits(GITHUB_USER, year, month, last_day) or {}

    repo_counts = {d: 0 for d in range(1, last_day + 1)}
    since = f"{year}-{month:02d}-01T00:00:00Z"
    until = f"{year}-{month:02d}-{last_day}T23:59:59Z"
    for repo in fetch_repos():
        items = gh_get(f"https://api.github.com/repos/{repo}/commits?since={since}&until={until}&per_page=100")
        if not isinstance(items, list):
            continue
        for item in items:
            try:
                d_str = item["commit"]["author"]["date"]
                dt = datetime.datetime.fromisoformat(d_str.replace("Z", "+00:00"))
                local_dt = dt.astimezone(datetime.timezone(datetime.timedelta(hours=-3)))
                if local_dt.year == year and local_dt.month == month:
                    repo_counts[local_dt.day] += 1
            except Exception:
                pass

    for d in range(1, last_day + 1):
        counts[d] = max(gql_counts.get(d, 0), search_counts.get(d, 0), repo_counts.get(d, 0))

    return counts

W, GROUND_Y, H = 980, 290, 360
LOT_W, GAP, ML = 26, 4, 20
FONT = "monospace"

def adjust_color(hex_color, amount):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r = max(0, min(255, r + amount))
    g = max(0, min(255, g + amount))
    b = max(0, min(255, b + amount))
    return f"#{r:02x}{g:02x}{b:02x}"

def building_height(commits):
    if commits <= 1:
        return 0
    if commits <= 3:
        return 60
    if commits <= 6:
        return 110
    if commits <= 10:
        return 160
    if commits <= 15:
        return 210
    return 310

def draw_sky(o, svg_w):
    o.append(f'<defs>'
             f'<linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0%" stop-color="var(--sky-top)"/>'
             f'<stop offset="100%" stop-color="var(--sky-bottom)"/>'
             f'</linearGradient>'
             f'<filter id="sunGlow"><feGaussianBlur stdDeviation="6" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
             f'<filter id="moonGlow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
             f'</defs>')
    o.append(f'<rect width="{svg_w}" height="{H}" fill="url(#skyGrad)"/>')
    o.append(f'<circle cx="120" cy="80" r="22" fill="#f59e0b" opacity="var(--sun-opacity)" filter="url(#sunGlow)"/>')
    o.append(f'<path d="M 120 70 A 15 15 0 1 0 135 85 A 12 12 0 1 1 120 70" fill="#e2e8f0" opacity="var(--moon-opacity)" filter="url(#moonGlow)"/>')
    o.append(f'<g opacity="var(--stars-opacity)">')
    rng = random.Random(42)
    for _ in range(90):
        sx, sy = rng.randint(0, svg_w), rng.randint(0, GROUND_Y - 20)
        op, r = round(rng.uniform(0.2, 0.9), 2), round(rng.uniform(0.5, 1.5), 1)
        o.append(f'<circle cx="{sx}" cy="{sy}" r="{r}" fill="#ffffff" opacity="{op}"/>')
    o.append(f'</g>')

def draw_street(o, svg_w):
    o.append(f'<rect x="0" y="{GROUND_Y}" width="{svg_w}" height="8" fill="#475569"/>')
    o.append(f'<rect x="0" y="{GROUND_Y+8}" width="{svg_w}" height="28" fill="#1e293b"/>')
    o.append(f'<line x1="0" y1="{GROUND_Y+22}" x2="{svg_w}" y2="{GROUND_Y+22}" stroke="#e2e8f0" stroke-width="2" stroke-dasharray="12,12"/>')

def draw_park(o, x):
    o.append(f'<rect x="{x}" y="{GROUND_Y-6}" width="{LOT_W}" height="6" fill="#15803d" rx="1"/>')
    bx = x + 3
    o.append(f'<rect x="{bx}" y="{GROUND_Y-9}" width="6" height="3" fill="#b45309"/>')
    o.append(f'<line x1="{bx}" y1="{GROUND_Y-9}" x2="{bx}" y2="{GROUND_Y-6}" stroke="#78350f" stroke-width="1"/>')
    o.append(f'<line x1="{bx+6}" y1="{GROUND_Y-9}" x2="{bx+6}" y2="{GROUND_Y-6}" stroke="#78350f" stroke-width="1"/>')
    tx = x + 18
    o.append(f'<rect x="{tx-1}" y="{GROUND_Y-16}" width="2" height="10" fill="#78350f"/>')
    o.append(f'<circle cx="{tx}" cy="{GROUND_Y-19}" r="7" fill="#16a34a"/>')
    o.append(f'<circle cx="{tx-3}" cy="{GROUND_Y-22}" r="5" fill="#22c55e"/>')

def draw_construction(o, x):
    o.append(f'<rect x="{x}" y="{GROUND_Y-40}" width="{LOT_W}" height="40" fill="none" stroke="#475569" stroke-width="1" stroke-dasharray="3,3" rx="1"/>')
    mx = x + LOT_W // 2
    o.append(f'<line x1="{mx}" y1="{GROUND_Y-40}" x2="{mx}" y2="{GROUND_Y-52}" stroke="#64748b" stroke-width="1.5"/>')
    o.append(f'<line x1="{mx}" y1="{GROUND_Y-52}" x2="{mx+10}" y2="{GROUND_Y-52}" stroke="#64748b" stroke-width="1.5"/>')

def draw_road_lamp(o, x):
    lx = x + LOT_W // 2
    o.append(f'<line x1="{lx}" y1="{GROUND_Y}" x2="{lx}" y2="{GROUND_Y-24}" stroke="#64748b" stroke-width="1.5"/>')
    o.append(f'<path d="M {lx} {GROUND_Y-24} Q {lx+5} {GROUND_Y-26} {lx+8} {GROUND_Y-22}" fill="none" stroke="#64748b" stroke-width="1.5"/>')
    o.append(f'<circle cx="{lx+8}" cy="{GROUND_Y-21}" r="2" fill="#fef08a"/>')
    o.append(f'<polygon points="{lx+8},{GROUND_Y-20} {lx-4},{GROUND_Y} {lx+20},{GROUND_Y}" fill="#fef08a" opacity="var(--street-lamp-glow)" style="mix-blend-mode: screen;"/>')

def draw_detailed_building(o, x, commits, day_seed):
    h = building_height(commits)
    y = GROUND_Y - h
    w = LOT_W
    style = day_seed % 4
    
    palettes = [
        ["#3b82f6", "#2563eb", "#1d4ed8"],
        ["#b45309", "#92400e", "#78350f"],
        ["#8b5cf6", "#7c3aed", "#6d28d9"],
        ["#0d9488", "#0f766e", "#115e59"]
    ]
    colors = palettes[style]
    
    o.append(f'<defs>'
             f'<linearGradient id="grad_{day_seed}" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0%" stop-color="{colors[0]}"/>'
             f'<stop offset="100%" stop-color="{colors[2]}"/>'
             f'</linearGradient>'
             f'</defs>')
    
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#grad_{day_seed})" rx="1"/>')
    o.append(f'<rect x="{x+w-4}" y="{y}" width="4" height="{h}" fill="#000000" opacity="0.2"/>')
    o.append(f'<rect x="{x+w//2-3}" y="{GROUND_Y-8}" width="6" height="8" fill="#1e293b"/>')
    o.append(f'<rect x="{x+w//2-2}" y="{GROUND_Y-7}" width="2" height="7" fill="var(--window-glow)" opacity="var(--window-glow-op)"/>')
    
    win_color = "var(--window-glow)"
    win_opacity = "var(--window-glow-op)"
    rng = random.Random(day_seed + 100)
    
    if style == 0:
        cols = 3
        rows = max(1, (h - 15) // 10)
        ww, wh = 4, 6
        for r in range(rows):
            for c in range(cols):
                if rng.random() < 0.75:
                    wx = x + 3 + c * 7
                    wy = y + 8 + r * 9
                    o.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="{win_color}" opacity="{win_opacity}"/>')
        o.append(f'<line x1="{x+w//2}" y1="{y}" x2="{x+w//2}" y2="{y-15}" stroke="#94a3b8" stroke-width="1.5"/>')
        o.append(f'<circle cx="{x+w//2}" cy="{y-15}" r="2" fill="#ef4444"/>')
        
    elif style == 1:
        cols = 2
        rows = max(1, (h - 15) // 12)
        ww, wh = 6, 8
        for r in range(rows):
            for c in range(cols):
                if rng.random() < 0.8:
                    wx = x + 4 + c * 11
                    wy = y + 8 + r * 11
                    o.append(f'<path d="M {wx} {wy+wh} L {wx} {wy+3} A {ww/2} {ww/2} 0 0 1 {wx+ww} {wy+3} L {wx+ww} {wy+wh} Z" fill="{win_color}" opacity="{win_opacity}"/>')
        o.append(f'<polygon points="{x-2},{y} {x+w//2},{y-10} {x+w+2},{y}" fill="{colors[1]}" stroke="#1e293b" stroke-width="1"/>')
        
    elif style == 2:
        cols = 2
        rows = max(1, (h - 15) // 14)
        ww, wh = 8, 10
        for r in range(rows):
            for c in range(cols):
                if rng.random() < 0.7:
                    wx = x + 4 + c * 10
                    wy = y + 8 + r * 13
                    o.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="{win_color}" opacity="{win_opacity}"/>')
                    o.append(f'<line x1="{wx}" y1="{wy+wh//2}" x2="{wx+ww}" y2="{wy+wh//2}" stroke="{colors[2]}" stroke-width="0.5"/>')
        o.append(f'<rect x="{x+4}" y="{y-8}" width="8" height="8" fill="#64748b" rx="1"/>')
        o.append(f'<line x1="{x+5}" y1="{y}" x2="{x+5}" y2="{y-8}" stroke="#475569" stroke-width="1"/>')
        o.append(f'<line x1="{x+11}" y1="{y}" x2="{x+11}" y2="{y-8}" stroke="#475569" stroke-width="1"/>')
        
    else:
        cols = 2
        rows = max(1, (h - 15) // 15)
        ww, wh = 6, 8
        for r in range(rows):
            for c in range(cols):
                wx = x + 4 + c * 11
                wy = y + 8 + r * 14
                if rng.random() < 0.8:
                    o.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="{win_color}" opacity="{win_opacity}"/>')
                o.append(f'<rect x="{wx-1}" y="{wy+wh}" width="{ww+2}" height="2" fill="#cbd5e1"/>')
        o.append(f'<path d="M {x+2} {y} A {w//2-2} {w//2-2} 0 0 1 {x+w-2} {y} Z" fill="{colors[1]}"/>')

def generate_svg(year, month, counts):
    last_day = calendar.monthrange(year, month)[1]
    today = datetime.date.today()
    mname = datetime.date(year, month, 1).strftime("%B %Y")
    
    svg_w = ML * 2 + last_day * (LOT_W + GAP) - GAP
    svg_w = max(W, svg_w)
    
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    br_now = utc_now - datetime.timedelta(hours=3)
    current_hour = br_now.hour
    is_daytime = 6 <= current_hour < 18
    
    if is_daytime:
        default_theme = """
    :root {
      --sky-top: #7dd3fc;
      --sky-bottom: #e0f2fe;
      --stars-opacity: 0;
      --sun-opacity: 1;
      --moon-opacity: 0;
      --window-glow: #ffffff;
      --window-glow-op: 0.3;
      --bird-opacity: 1;
      --plane-opacity: 0;
      --street-lamp-glow: 0;
      --car-headlight-glow: 0;
    }
"""
    else:
        default_theme = """
    :root {
      --sky-top: #070b19;
      --sky-bottom: #1e1b4b;
      --stars-opacity: 0.85;
      --sun-opacity: 0;
      --moon-opacity: 0.9;
      --window-glow: #fef08a;
      --window-glow-op: 0.95;
      --bird-opacity: 0;
      --plane-opacity: 1;
      --street-lamp-glow: 0.8;
      --car-headlight-glow: 0.6;
    }
"""

    css_rules = f"""  <style>
    {default_theme}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --sky-top: #070b19;
        --sky-bottom: #1e1b4b;
        --stars-opacity: 0.85;
        --sun-opacity: 0;
        --moon-opacity: 0.9;
        --window-glow: #fef08a;
        --window-glow-op: 0.95;
        --bird-opacity: 0;
        --plane-opacity: 1;
        --street-lamp-glow: 0.8;
        --car-headlight-glow: 0.6;
      }}
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --sky-top: #7dd3fc;
        --sky-bottom: #e0f2fe;
        --stars-opacity: 0;
        --sun-opacity: 1;
        --moon-opacity: 0;
        --window-glow: #ffffff;
        --window-glow-op: 0.3;
        --bird-opacity: 1;
        --plane-opacity: 0;
        --street-lamp-glow: 0;
        --car-headlight-glow: 0;
      }}
    }}
  </style>"""

    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{H}" viewBox="0 0 {svg_w} {H}">')
    o.append(css_rules)
    
    draw_sky(o, svg_w)
    
    o.append(f'<g opacity="var(--bird-opacity)">')
    o.append(f'  <path d="M 0 0 Q 3 -5 6 0 Q 9 -5 12 0 Q 9 -2 6 -1 Q 3 -2 0 0 Z" fill="#334155">')
    o.append(f'    <animateTransform attributeName="transform" type="translate" from="-40 80" to="{svg_w + 40} 60" dur="15s" repeatCount="indefinite"/>')
    o.append(f'  </path>')
    o.append(f'  <path d="M 0 0 Q 3 -5 6 0 Q 9 -5 12 0 Q 9 -2 6 -1 Q 3 -2 0 0 Z" fill="#334155">')
    o.append(f'    <animateTransform attributeName="transform" type="translate" from="-150 120" to="{svg_w + 40} 100" dur="18s" repeatCount="indefinite"/>')
    o.append(f'  </path>')
    o.append(f'</g>')
    o.append(f'<g opacity="var(--plane-opacity)">')
    o.append(f'  <animateTransform attributeName="transform" type="translate" from="-120 40" to="{svg_w + 120} 45" dur="14s" repeatCount="indefinite"/>')
    o.append(f'  <g transform="scale(-1, 1)">')
    o.append(f'    <path d="M 0 0 L 15 -2 L 20 -7 L 23 -7 L 21 -2 L 35 -2 L 37 -4 L 39 -4 L 38 1 L 18 1 L 16 4 L 13 4 L 14 1 L 0 0 Z" fill="#94a3b8"/>')
    o.append(f'    <circle cx="38" cy="-4" r="1.5" fill="#ef4444">')
    o.append(f'      <animate attributeName="opacity" values="0;1;0" dur="0.8s" repeatCount="indefinite"/>')
    o.append(f'    </circle>')
    o.append(f'    <circle cx="21" cy="-7" r="1.5" fill="#22c55e">')
    o.append(f'      <animate attributeName="opacity" values="0;1;0" dur="1s" repeatCount="indefinite"/>')
    o.append(f'    </circle>')
    o.append(f'  </g>')
    o.append(f'</g>')
    
    o.append(f'<text x="{svg_w//2}" y="32" text-anchor="middle" font-size="16" fill="#f8fafc" font-family="{FONT}" font-weight="bold">&#x1F3D9;&#xFE0F; GitHub City Skyline — {mname}</text>')
    
    draw_street(o, svg_w)
    
    for d in range(1, last_day + 1):
        x = ML + (d - 1) * (LOT_W + GAP)
        commits = counts.get(d, 0)
        cur = datetime.date(year, month, d)
        
        is_today = cur == today
        is_future = cur > today
        day_seed = (year * 100 + month) * 100 + d
        
        o.append(f'<g>')
        o.append(f'<title>Dia {d}: {commits} {"commit" if commits == 1 else "commits"}</title>')
        o.append(f'<line x1="{x + LOT_W//2}" y1="50" x2="{x + LOT_W//2}" y2="{GROUND_Y}" stroke="#334155" stroke-width="0.5" stroke-dasharray="2,4"/>')
        
        if is_future:
            draw_construction(o, x)
        elif commits == 0:
            if day_seed % 5 == 0:
                draw_road_lamp(o, x)
        elif commits == 1:
            draw_park(o, x)
        else:
            draw_detailed_building(o, x, commits, day_seed)
            h = building_height(commits)
            b_width = 14
            b_height = 10
            by = 42 if h >= 310 else (GROUND_Y - h - 16)
            o.append(f'<rect x="{x + LOT_W//2 - b_width//2}" y="{by}" width="{b_width}" height="{b_height}" fill="#f59e0b" rx="2"/>')
            o.append(f'<text x="{x + LOT_W//2}" y="{by + 8}" text-anchor="middle" font-size="8" fill="#0f172a" font-weight="bold" font-family="{FONT}">{commits}</text>')
        
        lbl_color = "#f59e0b" if is_today else "#94a3b8"
        font_w = "bold" if is_today else "normal"
        o.append(f'<text x="{x + LOT_W//2}" y="{GROUND_Y + 20}" text-anchor="middle" font-size="10" fill="{lbl_color}" font-weight="{font_w}" font-family="{FONT}">{d}</text>')
        
        if is_today:
            o.append(f'<polygon points="{x+LOT_W//2-4},{GROUND_Y+25} {x+LOT_W//2+4},{GROUND_Y+25} {x+LOT_W//2},{GROUND_Y+30}" fill="#f59e0b"/>')

        o.append(f'</g>')

    o.append(f'<g>')
    o.append(f'  <g>')
    o.append(f'    <animateTransform attributeName="transform" type="translate" from="{svg_w + 20} {GROUND_Y + 4}" to="-20 {GROUND_Y + 4}" dur="25s" repeatCount="indefinite"/>')
    o.append(f'    <circle cx="0" cy="-6" r="1.8" fill="#ec4899"/>')
    o.append(f'    <line x1="0" y1="-4.2" x2="0" y2="-1" stroke="#ec4899" stroke-width="1.6"/>')
    o.append(f'    <line x1="0" y1="-1" x2="-1.2" y2="2" stroke="#ec4899" stroke-width="1.2">')
    o.append(f'      <animateTransform attributeName="transform" type="rotate" values="15 0 -1; -15 0 -1; 15 0 -1" dur="0.6s" repeatCount="indefinite"/>')
    o.append(f'    </line>')
    o.append(f'    <line x1="0" y1="-1" x2="1.2" y2="2" stroke="#ec4899" stroke-width="1.2">')
    o.append(f'      <animateTransform attributeName="transform" type="rotate" values="-15 0 -1; 15 0 -1; -15 0 -1" dur="0.6s" repeatCount="indefinite"/>')
    o.append(f'    </line>')
    o.append(f'  </g>')
    o.append(f'  <g>')
    o.append(f'    <animateTransform attributeName="transform" type="translate" from="-100 {GROUND_Y + 4}" to="{svg_w + 20} {GROUND_Y + 4}" dur="22s" repeatCount="indefinite"/>')
    o.append(f'    <circle cx="0" cy="-6" r="1.8" fill="#14b8a6"/>')
    o.append(f'    <line x1="0" y1="-4.2" x2="0" y2="-1" stroke="#14b8a6" stroke-width="1.6"/>')
    o.append(f'    <line x1="0" y1="-1" x2="-1.2" y2="2" stroke="#14b8a6" stroke-width="1.2">')
    o.append(f'      <animateTransform attributeName="transform" type="rotate" values="15 0 -1; -15 0 -1; 15 0 -1" dur="0.5s" repeatCount="indefinite"/>')
    o.append(f'    </line>')
    o.append(f'    <line x1="0" y1="-1" x2="1.2" y2="2" stroke="#14b8a6" stroke-width="1.2">')
    o.append(f'      <animateTransform attributeName="transform" type="rotate" values="-15 0 -1; 15 0 -1; -15 0 -1" dur="0.5s" repeatCount="indefinite"/>')
    o.append(f'    </line>')
    o.append(f'  </g>')
    o.append(f'  <g>')
    o.append(f'    <animateTransform attributeName="transform" type="translate" from="{svg_w + 120} {GROUND_Y + 4}" to="-20 {GROUND_Y + 4}" dur="28s" repeatCount="indefinite"/>')
    o.append(f'    <circle cx="0" cy="-6" r="1.8" fill="#a855f7"/>')
    o.append(f'    <line x1="0" y1="-4.2" x2="0" y2="-1" stroke="#a855f7" stroke-width="1.6"/>')
    o.append(f'    <line x1="0" y1="-1" x2="-1.2" y2="2" stroke="#a855f7" stroke-width="1.2">')
    o.append(f'      <animateTransform attributeName="transform" type="rotate" values="15 0 -1; -15 0 -1; 15 0 -1" dur="0.7s" repeatCount="indefinite"/>')
    o.append(f'    </line>')
    o.append(f'    <line x1="0" y1="-1" x2="1.2" y2="2" stroke="#a855f7" stroke-width="1.2">')
    o.append(f'      <animateTransform attributeName="transform" type="rotate" values="-15 0 -1; 15 0 -1; -15 0 -1" dur="0.7s" repeatCount="indefinite"/>')
    o.append(f'    </line>')
    o.append(f'  </g>')
    o.append(f'  <g>')
    o.append(f'    <animateTransform attributeName="transform" type="translate" from="-220 {GROUND_Y + 4}" to="{svg_w + 20} {GROUND_Y + 4}" dur="26s" repeatCount="indefinite"/>')
    o.append(f'    <circle cx="0" cy="-6" r="1.8" fill="#f97316"/>')
    o.append(f'    <line x1="0" y1="-4.2" x2="0" y2="-1" stroke="#f97316" stroke-width="1.6"/>')
    o.append(f'    <line x1="0" y1="-1" x2="-1.2" y2="2" stroke="#f97316" stroke-width="1.2">')
    o.append(f'      <animateTransform attributeName="transform" type="rotate" values="15 0 -1; -15 0 -1; 15 0 -1" dur="0.6s" repeatCount="indefinite"/>')
    o.append(f'    </line>')
    o.append(f'    <line x1="0" y1="-1" x2="1.2" y2="2" stroke="#f97316" stroke-width="1.2">')
    o.append(f'      <animateTransform attributeName="transform" type="rotate" values="-15 0 -1; 15 0 -1; -15 0 -1" dur="0.6s" repeatCount="indefinite"/>')
    o.append(f'    </line>')
    o.append(f'  </g>')
    o.append(f'</g>')
    
    o.append(f'<g>')
    o.append(f'  <g>')
    o.append(f'    <animateTransform attributeName="transform" type="translate" from="{svg_w + 30} {GROUND_Y + 10}" to="-30 {GROUND_Y + 10}" dur="12s" repeatCount="indefinite"/>')
    o.append(f'    <rect x="-11" y="0" width="22" height="7" fill="#ef4444" rx="1.5"/>')
    o.append(f'    <path d="M -7 0 L -4 -4 L 4 -4 L 7 0 Z" fill="#ef4444"/>')
    o.append(f'    <path d="M -5 0 L -3 -3 L 3 -3 L 5 0 Z" fill="#e2e8f0" opacity="0.75"/>')
    o.append(f'    <circle cx="-5" cy="7" r="2.5" fill="#0f172a"/>')
    o.append(f'    <circle cx="5" cy="7" r="2.5" fill="#0f172a"/>')
    o.append(f'    <polygon points="-11,2 -26,0 -26,6 -11,5" fill="#fef08a" opacity="var(--car-headlight-glow)"/>')
    o.append(f'  </g>')
    o.append(f'  <g>')
    o.append(f'    <animateTransform attributeName="transform" type="translate" from="-150 {GROUND_Y + 21}" to="{svg_w + 30} {GROUND_Y + 21}" dur="10s" repeatCount="indefinite"/>')
    o.append(f'    <rect x="-11" y="0" width="22" height="7" fill="#3b82f6" rx="1.5"/>')
    o.append(f'    <path d="M -7 0 L -4 -4 L 4 -4 L 7 0 Z" fill="#3b82f6"/>')
    o.append(f'    <path d="M -5 0 L -3 -3 L 3 -3 L 5 0 Z" fill="#e2e8f0" opacity="0.75"/>')
    o.append(f'    <circle cx="-5" cy="7" r="2.5" fill="#0f172a"/>')
    o.append(f'    <circle cx="5" cy="7" r="2.5" fill="#0f172a"/>')
    o.append(f'    <polygon points="11,2 26,0 26,6 11,5" fill="#fef08a" opacity="var(--car-headlight-glow)"/>')
    o.append(f'  </g>')
    o.append(f'  <g>')
    o.append(f'    <animateTransform attributeName="transform" type="translate" from="{svg_w + 250} {GROUND_Y + 10}" to="-30 {GROUND_Y + 10}" dur="14s" repeatCount="indefinite"/>')
    o.append(f'    <rect x="-11" y="0" width="22" height="7" fill="#f59e0b" rx="1.5"/>')
    o.append(f'    <path d="M -7 0 L -4 -4 L 4 -4 L 7 0 Z" fill="#f59e0b"/>')
    o.append(f'    <path d="M -5 0 L -3 -3 L 3 -3 L 5 0 Z" fill="#e2e8f0" opacity="0.75"/>')
    o.append(f'    <circle cx="-5" cy="7" r="2.5" fill="#0f172a"/>')
    o.append(f'    <circle cx="5" cy="7" r="2.5" fill="#0f172a"/>')
    o.append(f'    <polygon points="-11,2 -26,0 -26,6 -11,5" fill="#fef08a" opacity="var(--car-headlight-glow)"/>')
    o.append(f'  </g>')
    o.append(f'  <g>')
    o.append(f'    <animateTransform attributeName="transform" type="translate" from="-400 {GROUND_Y + 21}" to="{svg_w + 30} {GROUND_Y + 21}" dur="13s" repeatCount="indefinite"/>')
    o.append(f'    <rect x="-11" y="0" width="22" height="7" fill="#10b981" rx="1.5"/>')
    o.append(f'    <path d="M -7 0 L -4 -4 L 4 -4 L 7 0 Z" fill="#10b981"/>')
    o.append(f'    <path d="M -5 0 L -3 -3 L 3 -3 L 5 0 Z" fill="#e2e8f0" opacity="0.75"/>')
    o.append(f'    <circle cx="-5" cy="7" r="2.5" fill="#0f172a"/>')
    o.append(f'    <circle cx="5" cy="7" r="2.5" fill="#0f172a"/>')
    o.append(f'    <polygon points="11,2 26,0 26,6 11,5" fill="#fef08a" opacity="var(--car-headlight-glow)"/>')
    o.append(f'  </g>')
    o.append(f'</g>')
    
    ly = H - 16
    items = [
        ("#1e293b", "0 commits"),
        ("#16a34a", "1 commit (Praça)"),
        ("#3b82f6", "2-3 commits"),
        ("#8b5cf6", "4-6 commits"),
        ("#0d9488", "7-10 commits"),
        ("#f59e0b", "11+ commits")
    ]
    lx = ML
    for color, label in items:
        o.append(f'<rect x="{lx}" y="{ly-8}" width="10" height="8" fill="{color}" rx="1" stroke="#475569" stroke-width="0.5"/>')
        o.append(f'<text x="{lx+14}" y="{ly-1}" font-size="9" fill="#94a3b8" font-family="{FONT}">{label}</text>')
        lx += 145
        
    o.append("</svg>")
    return "\n".join(o)

def generate_html(all_data):
    data_json = json.dumps(all_data)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>GitHub City Skyline</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #070b19; color: #f8fafc; font-family: monospace; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 24px; }}
h1 {{ font-size: 1.6rem; color: #f8fafc; margin-bottom: 20px; letter-spacing: 2px; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }}
.controls {{ display: flex; gap: 12px; align-items: center; margin-bottom: 24px; background: #0f172a; padding: 10px 20px; border-radius: 8px; border: 1px solid #1e293b; }}
label {{ color: #94a3b8; font-size: 0.95rem; }}
select {{ background: #1e293b; color: #f8fafc; border: 1px solid #475569; border-radius: 6px; padding: 8px 16px; font-family: monospace; font-size: 0.95rem; cursor: pointer; outline: none; }}
select:focus {{ border-color: #3b82f6; }}
.city-wrapper {{ width: 100%; max-width: 1000px; overflow-x: auto; background: #0f172a; border-radius: 12px; border: 1px solid #1e293b; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); padding: 15px; margin-bottom: 20px; }}
.city-wrapper::-webkit-scrollbar {{ height: 8px; }}
.city-wrapper::-webkit-scrollbar-track {{ background: #0f172a; }}
.city-wrapper::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 4px; }}
.city-wrapper::-webkit-scrollbar-thumb:hover {{ background: #475569; }}
</style>
</head>
<body>
<h1>&#x1F3D9;&#xFE0F; GitHub City Skyline</h1>
<div class="controls">
  <label for="sel">Mês Selecionado:</label>
  <select id="sel"></select>
</div>
<div class="city-wrapper" id="container"></div>
<script>
const DATA = {data_json};

function adjustColor(hex, amount) {{
    hex = hex.replace('#', '');
    let r = parseInt(hex.substring(0, 2), 16) + amount;
    let g = parseInt(hex.substring(2, 4), 16) + amount;
    let b = parseInt(hex.substring(4, 6), 16) + amount;
    r = Math.max(0, Math.min(255, r));
    g = Math.max(0, Math.min(255, g));
    b = Math.max(0, Math.min(255, b));
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}}

function render(yr, mo, counts) {{
    const lastDay = new Date(yr, mo, 0).getDate();
    const today = new Date();
    const mNames = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
    const mname = mNames[mo-1] + " " + yr;
    
    const W = 980, GROUND_Y = 290, H = 360, LOT_W = 26, GAP = 4, ML = 20;
    const svgW = Math.max(W, ML * 2 + lastDay * (LOT_W + GAP) - GAP);
    
    let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${{svgW}}" height="${{H}}" viewBox="0 0 ${{svgW}} ${{H}}">`;
    svg += `<defs>
      <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#070b19"/>
        <stop offset="60%" stop-color="#10172a"/>
        <stop offset="100%" stop-color="#1e1b4b"/>
      </linearGradient>
    </defs>`;
    svg += `<rect width="${{svgW}}" height="${{H}}" fill="url(#skyGrad)"/>`;
    
    let seed = 42;
    function rng() {{
        let x = Math.sin(seed++) * 10000;
        return x - Math.floor(x);
    }}
    for(let i=0; i<90; i++) {{
        let sx = rng() * svgW, sy = rng() * (GROUND_Y - 20);
        let op = 0.2 + rng() * 0.7, r = 0.5 + rng() * 1.0;
        svg += `<circle cx="${{sx}}" cy="${{sy}}" r="${{r}}" fill="#ffffff" opacity="${{op}}"/>`;
    }}
    
    svg += `<text x="${{svgW/2}}" y="32" text-anchor="middle" font-size="16" fill="#f8fafc" font-family="monospace" font-weight="bold">&#x1F3D9;&#xFE0F; GitHub City Skyline — ${{mname}}</text>`;
    svg += `<rect x="0" y="${{GROUND_Y}}" width="${{svgW}}" height="8" fill="#475569"/>`;
    svg += `<rect x="0" y="${{GROUND_Y+8}}" width="${{svgW}}" height="28" fill="#1e293b"/>`;
    svg += `<line x1="0" y1="${{GROUND_Y+22}}" x2="${{svgW}}" y2="${{GROUND_Y+22}}" stroke="#e2e8f0" stroke-width="2" stroke-dasharray="12,12"/>`;
    
    for (let d = 1; d <= lastDay; d++) {{
        const x = ML + (d - 1) * (LOT_W + GAP);
        const commits = counts[d] || 0;
        const curDate = new Date(yr, mo - 1, d);
        const tdToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        const isToday = curDate.getTime() === tdToday.getTime();
        const isFuture = curDate > tdToday;
        const daySeed = (yr * 100 + mo) * 100 + d;
        
        svg += `<g>`;
        svg += `<title>Dia ${{d}}: ${{commits}} ${{commits === 1 ? 'commit' : 'commits'}}</title>`;
        svg += `<line x1="${{x + LOT_W/2}}" y1="50" x2="${{x + LOT_W/2}}" y2="${{GROUND_Y}}" stroke="#334155" stroke-width="0.5" stroke-dasharray="2,4"/>`;
        
        if (isFuture) {{
            svg += `<rect x="${{x}}" y="${{GROUND_Y-40}}" width="${{LOT_W}}" height="40" fill="none" stroke="#475569" stroke-width="1" stroke-dasharray="3,3" rx="1"/>`;
            const mx = x + LOT_W / 2;
            svg += `<line x1="${{mx}}" y1="${{GROUND_Y-40}}" x2="${{mx}}" y2="${{GROUND_Y-52}}" stroke="#64748b" stroke-width="1.5"/>`;
            svg += `<line x1="${{mx}}" y1="${{GROUND_Y-52}}" x2="${{mx+10}}" y2="${{GROUND_Y-52}}" stroke="#64748b" stroke-width="1.5"/>`;
        }} else if (commits === 0) {{
            if (daySeed % 5 === 0) {{
                const lx = x + LOT_W / 2;
                svg += `<line x1="${{lx}}" y1="${{GROUND_Y}}" x2="${{lx}}" y2="${{GROUND_Y-24}}" stroke="#64748b" stroke-width="1.5"/>`;
                svg += `<path d="M ${{lx}} ${{GROUND_Y-24}} Q ${{lx+5}} ${{GROUND_Y-26}} ${{lx+8}} ${{GROUND_Y-22}}" fill="none" stroke="#64748b" stroke-width="1.5"/>`;
                svg += `<circle cx="${{lx+8}}" cy="${{GROUND_Y-21}}" r="2" fill="#fef08a"/>`;
            }}
        }} else if (commits === 1) {{
            svg += `<rect x="${{x}}" y="${{GROUND_Y-6}}" width="${{LOT_W}}" height="6" fill="#15803d" rx="1"/>`;
            svg += `<rect x="${{x+3}}" y="${{GROUND_Y-9}}" width="6" height="3" fill="#b45309"/>`;
            svg += `<line x1="${{x+3}}" y1="${{GROUND_Y-9}}" x2="${{x+3}}" y2="${{GROUND_Y-6}}" stroke="#78350f" stroke-width="1"/>`;
            svg += `<line x1="${{x+9}}" y1="${{GROUND_Y-9}}" x2="${{x+9}}" y2="${{GROUND_Y-6}}" stroke="#78350f" stroke-width="1"/>`;
            svg += `<rect x="${{x+17}}" y="${{GROUND_Y-16}}" width="2" height="10" fill="#78350f"/>`;
            svg += `<circle cx="${{x+18}}" cy="${{GROUND_Y-19}}" r="7" fill="#16a34a"/>`;
            svg += `<circle cx="${{x+15}}" cy="${{GROUND_Y-22}}" r="5" fill="#22c55e"/>`;
        }} else {{
            let h = commits <= 3 ? 60 : commits <= 6 ? 110 : commits <= 10 ? 160 : commits <= 15 ? 210 : 310;
            const yPos = GROUND_Y - h;
            const style = daySeed % 4;
            const palettes = [
                ["#3b82f6", "#2563eb", "#1d4ed8"],
                ["#b45309", "#92400e", "#78350f"],
                ["#8b5cf6", "#7c3aed", "#6d28d9"],
                ["#0d9488", "#0f766e", "#115e59"]
            ];
            const colors = palettes[style];
            
            svg += `<defs>
              <linearGradient id="grad_h_${{daySeed}}" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="${{colors[0]}}"/>
                <stop offset="100%" stop-color="${{colors[2]}}"/>
              </linearGradient>
            </defs>`;
            svg += `<rect x="${{x}}" y="${{yPos}}" width="${{LOT_W}}" height="${{h}}" fill="url(#grad_h_${{daySeed}})" rx="1"/>`;
            svg += `<rect x="${{x+LOT_W-4}}" y="${{yPos}}" width="4" height="${{h}}" fill="#000000" opacity="0.2"/>`;
            svg += `<rect x="${{x+LOT_W/2-3}}" y="${{GROUND_Y-8}}" width="6" height="8" fill="#1e293b"/>`;
            svg += `<rect x="${{x+LOT_W/2-2}}" y="${{GROUND_Y-7}}" width="2" height="7" fill="#fef08a" opacity="0.8"/>`;
            
            let winSeed = daySeed + 100;
            function rngWin() {{
                let x = Math.sin(winSeed++) * 10000;
                return x - Math.floor(x);
            }}
            
            if (style === 0) {{
                const cols = 3, rows = Math.max(1, Math.floor((h - 15) / 10));
                for(let r=0; r<rows; r++) {{
                    for(let c=0; c<cols; c++) {{
                        if (rngWin() < 0.75) {{
                            svg += `<rect x="${{x+3+c*7}}" y="${{yPos+8+r*9}}" width="4" height="6" fill="#fef08a" opacity="0.9"/>`;
                        }}
                    }}
                }}
                svg += `<line x1="${{x+LOT_W/2}}" y1="${{yPos}}" x2="${{x+LOT_W/2}}" y2="${{yPos-15}}" stroke="#94a3b8" stroke-width="1.5"/>`;
                svg += `<circle cx="${{x+LOT_W/2}}" cy="${{yPos-15}}" r="2" fill="#ef4444"/>`;
            }} else if (style === 1) {{
                const cols = 2, rows = Math.max(1, Math.floor((h - 15) / 12));
                for(let r=0; r<rows; r++) {{
                    for(let c=0; c<cols; c++) {{
                        if (rngWin() < 0.8) {{
                            let wx = x+4+c*11, wy = yPos+8+r*11;
                            svg += `<path d="M ${{wx}} ${{wy+8}} L ${{wx}} ${{wy+3}} A 3 3 0 0 1 ${{wx+6}} ${{wy+3}} L ${{wx+6}} ${{wy+8}} Z" fill="#fef08a" opacity="0.9"/>`;
                        }}
                    }}
                }}
                svg += `<polygon points="${{x-2}},${{yPos}} ${{x+LOT_W/2}},${{yPos-10}} ${{x+LOT_W+2}},${{yPos}}" fill="${{colors[1]}}" stroke="#1e293b" stroke-width="1"/>`;
            }} else if (style === 2) {{
                const cols = 2, rows = Math.max(1, Math.floor((h - 15) / 14));
                for(let r=0; r<rows; r++) {{
                    for(let c=0; c<cols; c++) {{
                        if (rngWin() < 0.7) {{
                            let wx = x+4+c*10, wy = yPos+8+r*13;
                            svg += `<rect x="${{wx}}" y="${{wy}}" width="8" height="10" fill="#fef08a" opacity="0.95"/>`;
                            svg += `<line x1="${{wx}}" y1="${{wy+5}}" x2="${{wx+8}}" y2="${{wy+5}}" stroke="${{colors[2]}}" stroke-width="0.5"/>`;
                        }}
                    }}
                }}
                svg += `<rect x="${{x+4}}" y="${{yPos-8}}" width="8" height="8" fill="#64748b" rx="1"/>`;
                svg += `<line x1="${{x+5}}" y1="${{yPos}}" x2="${{x+5}}" y2="${{yPos-8}}" stroke="#475569" stroke-width="1"/>`;
                svg += `<line x1="${{x+11}}" y1="${{yPos}}" x2="${{x+11}}" y2="${{yPos-8}}" stroke="#475569" stroke-width="1"/>`;
            }} else {{
                const cols = 2, rows = Math.max(1, Math.floor((h - 15) / 15));
                for(let r=0; r<rows; r++) {{
                    for(let c=0; c<cols; c++) {{
                        let wx = x+4+c*11, wy = yPos+8+r*14;
                        if (rngWin() < 0.8) {{
                            svg += `<rect x="${{wx}}" y="${{wy}}" width="6" height="8" fill="#fef08a" opacity="0.9"/>`;
                        }}
                        svg += `<rect x="${{wx-1}}" y="${{wy+8}}" width="8" height="2" fill="#cbd5e1"/>`;
                    }}
                }}
                svg += `<path d="M ${{x+2}} ${{yPos}} A ${{LOT_W/2-2}} ${{LOT_W/2-2}} 0 0 1 ${{x+LOT_W-2}} ${{yPos}} Z" fill="${{colors[1]}}"/>`;
            }}
            
            const bWidth = 14, bHeight = 10;
            const by = h >= 310 ? 42 : yPos - 16;
            svg += `<rect x="${{x + LOT_W/2 - bWidth/2}}" y="${{by}}" width="${{bWidth}}" height="${{bHeight}}" fill="#f59e0b" rx="2"/>`;
            svg += `<text x="${{x + LOT_W/2}}" y="${{by + 8}}" text-anchor="middle" font-size="8" fill="#0f172a" font-weight="bold" font-family="monospace">${{commits}}</text>`;
        }}
        
        let lblColor = isToday ? "#f59e0b" : "#94a3b8";
        let fontW = isToday ? "bold" : "normal";
        svg += `<text x="${{x + LOT_W/2}}" y="${{GROUND_Y+20}}" text-anchor="middle" font-size="10" fill="${{lblColor}}" font-weight="${{fontW}}" font-family="monospace">${{d}}</text>`;
        
        if (isToday) {{
            svg += `<polygon points="${{x+LOT_W/2-4}},${{GROUND_Y+25}} ${{x+LOT_W/2+4}},${{GROUND_Y+25}} ${{x+LOT_W/2}},${{GROUND_Y+30}}" fill="#f59e0b"/>`;
        }}
        
        svg += `</g>`;
    }}

    const ly = H - 16;
    const legendItems = [
        ["#1e293b", "0 commits"],
        ["#16a34a", "1 commit (Praça)"],
        ["#3b82f6", "2-3 commits"],
        ["#8b5cf6", "4-6 commits"],
        ["#0d9488", "7-10 commits"],
        ["#f59e0b", "11+ commits"]
    ];
    let lx = ML;
    legendItems.forEach(item => {{
        svg += `<rect x="${{lx}}" y="${{ly-8}}" width="10" height="8" fill="${{item[0]}}" rx="1" stroke="#475569" stroke-width="0.5"/>`;
        svg += `<text x="${{lx+14}}" y="${{ly-1}}" font-size="9" fill="#94a3b8" font-family="monospace">${{item[1]}}</text>`;
        lx += 145;
    }});
    
    svg += `</svg>`;
    return svg;
}}

const sel = document.getElementById("sel");
const keys = Object.keys(DATA).sort().reverse();
keys.forEach(k => {{
    const opt = document.createElement("option");
    opt.value = k; opt.textContent = k;
    sel.appendChild(opt);
}});

sel.addEventListener("change", () => {{
    const [y, m] = sel.value.split("-").map(Number);
    document.getElementById("container").innerHTML = render(y, m, DATA[sel.value] || {{}});
}});

if (keys.length > 0) {{
    sel.value = keys[0];
    sel.dispatchEvent(new Event("change"));
}}
</script>
</body>
</html>"""

def generate_procedural_paths_svg():
    TILE = 24
    COLS = 33
    ROWS = 11

    def slide_dest(grid, cx, cy, dx, dy):
        tx, ty = cx, cy
        while True:
            nx, ny = tx + dx, ty + dy
            if not (0 <= nx < COLS and 0 <= ny < ROWS):
                break
            if grid[ny][nx] == 0:
                break
            tx, ty = nx, ny
        return tx, ty

    def slide_cells(cx, cy, tx, ty):
        dx = 0 if tx == cx else (1 if tx > cx else -1)
        dy = 0 if ty == cy else (1 if ty > cy else -1)
        cells, x, y = [], cx, cy
        while (x, y) != (tx, ty):
            x += dx; y += dy
            cells.append((x, y))
        return cells

    def carve_maze():
        W, H = COLS, ROWS
        g = [[0]*W for _ in range(H)]
        room_cells = [(c, r) for r in range(1, H, 2) for c in range(1, W, 2)]
        in_maze = set()
        start = random.choice(room_cells)
        in_maze.add(start)
        g[start[1]][start[0]] = 1

        frontiers = []
        def add_frontiers(rc):
            c, r = rc
            for dc, dr in [(2,0),(-2,0),(0,2),(0,-2)]:
                nc, nr = c+dc, r+dr
                if 0 < nc < W and 0 < nr < H and (nc,nr) not in in_maze:
                    frontiers.append(((c+dc//2, r+dr//2), (nc, nr)))

        add_frontiers(start)
        while frontiers:
            random.shuffle(frontiers)
            wall, nxt = frontiers.pop()
            if nxt in in_maze:
                continue
            in_maze.add(nxt)
            g[nxt[1]][nxt[0]] = 1
            g[wall[1]][wall[0]] = 1
            add_frontiers(nxt)

        wall_candidates = [(c, r) for r in range(1, H-1) for c in range(1, W-1) if g[r][c] == 0]
        random.shuffle(wall_candidates)
        n_extra = max(6, len(wall_candidates) * 18 // 100)
        opened = 0
        for c, r in wall_candidates:
            if opened >= n_extra:
                break
            neighbors_open = sum(
                1 for dc, dr in [(1,0),(-1,0),(0,1),(0,-1)]
                if 0 <= c+dc < W and 0 <= r+dr < H and g[r+dr][c+dc] == 1
            )
            if neighbors_open >= 2:
                g[r][c] = 1
                opened += 1
        return g

    def build_room():
        for attempt in range(150):
            grid = carve_maze()
            all_stops = set()
            for r in range(1, ROWS-1):
                for c in range(1, COLS-1):
                    if grid[r][c] == 1:
                        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                            if grid[r+dy][c+dx] == 0:
                                all_stops.add((c, r))
                                break
                                
            adj = {p: [] for p in all_stops}
            for (cx, cy) in all_stops:
                for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    tx, ty = slide_dest(grid, cx, cy, dx, dy)
                    if (tx, ty) != (cx, cy) and (tx, ty) in all_stops:
                        adj[(cx, cy)].append(((tx, ty), slide_cells(cx, cy, tx, ty)))

            index = 0
            indices, lowlink = {}, {}
            on_stack = set()
            stack, sccs = [], []

            def strongconnect(v):
                nonlocal index
                indices[v] = index
                lowlink[v] = index
                index += 1
                stack.append(v)
                on_stack.add(v)

                for dest, _ in adj.get(v, []):
                    if dest not in indices:
                        strongconnect(dest)
                        lowlink[v] = min(lowlink[v], lowlink[dest])
                    elif dest in on_stack:
                        lowlink[v] = min(lowlink[v], indices[dest])

                if lowlink[v] == indices[v]:
                    scc = []
                    while True:
                        w = stack.pop()
                        on_stack.remove(w)
                        scc.append(w)
                        if w == v:
                            break
                    sccs.append(scc)

            for p in all_stops:
                if p not in indices:
                    strongconnect(p)

            sccs.sort(key=len, reverse=True)
            if not sccs or len(sccs[0]) < 8:
                continue

            best_scc = set(sccs[0])
            min_c = min(c for c, r in best_scc)
            max_c = max(c for c, r in best_scc)
            min_span = 20 if attempt < 40 else 14
            if (max_c - min_c) < min_span:
                continue

            scc_adj = {}
            for p in best_scc:
                scc_adj[p] = [(dest, cells) for dest, cells in adj[p] if dest in best_scc]

            crossed_cells = set()
            for src, edges in scc_adj.items():
                crossed_cells.add(src)
                for dest, cells in edges:
                    crossed_cells.add(dest)
                    crossed_cells.update(cells)

            new_grid = [row[:] for row in grid]
            for r in range(ROWS):
                for c in range(COLS):
                    if (c, r) not in crossed_cells:
                        new_grid[r][c] = 0

            valid = True
            for p in best_scc:
                for (dest, cells) in scc_adj[p]:
                    dx = 0 if dest[0] == p[0] else (1 if dest[0] > p[0] else -1)
                    dy = 0 if dest[1] == p[1] else (1 if dest[1] > p[1] else -1)
                    t_dest = slide_dest(new_grid, p[0], p[1], dx, dy)
                    if t_dest != dest:
                        valid = False
                        break
                if not valid:
                    break
            
            if not valid:
                continue

            start = random.choice(list(best_scc))
            all_coins = set(crossed_cells) - {start}
            coins = set(all_coins)
            path = [start]
            cur = start
            
            while coins:
                queue = [(cur, [])]
                visited = {cur}
                found = None
                while queue:
                    pos, steps = queue.pop(0)
                    for dest, cells in scc_adj.get(pos, []):
                        if any(c in coins for c in cells):
                            found = steps + [pos, dest]
                            break
                        if dest not in visited:
                            visited.add(dest)
                            queue.append((dest, steps + [pos]))
                    if found:
                        break
                if not found:
                    break
                for i in range(len(found) - 1):
                    p1, p2 = found[i], found[i+1]
                    for cell in slide_cells(p1[0], p1[1], p2[0], p2[1]):
                        coins.discard(cell)
                    path.append(p2)
                cur = found[-1]

            min_coins = 40 if attempt < 40 else 25
            min_path = 12 if attempt < 40 else 8
            if len(all_coins) >= min_coins and len(path) >= min_path:
                return new_grid, path, start[0], start[1], all_coins

        raise RuntimeError("Failed to generate procedural room")

    num_rooms = 3
    rooms = []
    for _ in range(num_rooms):
        grid, path, start_x, start_y, coins = build_room()
        rooms.append({
            "grid": grid,
            "path": path,
            "start": (start_x, start_y),
            "coins": list(coins)
        })
        
    v = 10.0
    pause = 0.12

    room_durations = []
    for r_data in rooms:
        path = r_data["path"]
        raw_durations = []
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i+1]
            d = abs(x2 - x1) + abs(y2 - y1)
            raw_durations.append(d / v + pause)
        total_raw = sum(raw_durations) if raw_durations else 1.0
        room_durations.append(0.4 + total_raw + 0.8)

    total_duration = sum(room_durations)
    
    styles = []
    keyframe_animations = []
    
    accumulated_time = 0.0
    for idx, r_data in enumerate(rooms):
        path = r_data["path"]
        grid = r_data["grid"]
        start_x, start_y = r_data["start"]
        room_duration = room_durations[idx]
        room_start_time = accumulated_time
        room_end_time = accumulated_time + room_duration
        accumulated_time += room_duration
        
        timeline = []
        cur_t = 0.4
        timeline.append({"time": cur_t, "x": start_x, "y": start_y, "scale": (1.0, 1.0), "dir": (1, 0)})
        
        dots_collected = {}
        
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i+1]
            dx = x2 - x1
            dy = y2 - y1
            d = abs(dx) + abs(dy)
            dir_norm = (1 if dx > 0 else (-1 if dx < 0 else 0), 1 if dy > 0 else (-1 if dy < 0 else 0))
            
            slide_dur = d / v
            pause_dur = pause
            
            if x1 == x2:
                step = 1 if y2 > y1 else -1
                for cy in range(y1 + step, y2 + step, step):
                    dist = abs(cy - y1)
                    t_collect = cur_t + (dist / d) * slide_dur
                    if (x1, cy) not in dots_collected:
                        dots_collected[(x1, cy)] = t_collect
            else:
                step = 1 if x2 > x1 else -1
                for cx in range(x1 + step, x2 + step, step):
                    dist = abs(cx - x1)
                    t_collect = cur_t + (dist / d) * slide_dur
                    if (cx, y1) not in dots_collected:
                        dots_collected[(cx, y1)] = t_collect
                        
            cur_t += slide_dur
            timeline.append({"time": cur_t, "x": x2, "y": y2, "scale": (1.0, 1.0), "dir": dir_norm})
            
            if dx != 0:
                sq_x, sq_y = 0.8, 1.2
                st_x, st_y = 1.1, 0.95
            else:
                sq_x, sq_y = 1.2, 0.8
                st_x, st_y = 0.95, 1.1
                
            timeline.append({"time": cur_t + 0.04, "x": x2, "y": y2, "scale": (sq_x, sq_y), "dir": dir_norm})
            timeline.append({"time": cur_t + 0.08, "x": x2, "y": y2, "scale": (st_x, st_y), "dir": dir_norm})
            
            cur_t += pause_dur
            timeline.append({"time": cur_t, "x": x2, "y": y2, "scale": (1.0, 1.0), "dir": dir_norm})
            
        room_start_pct = (room_start_time / total_duration) * 100.0
        room_end_pct = (room_end_time / total_duration) * 100.0
        
        player_kf = []
        for step in timeline:
            t_abs = room_start_time + step["time"]
            pct = (t_abs / total_duration) * 100.0
            px = step["x"] * TILE + TILE / 2
            py = step["y"] * TILE + TILE / 2
            sx, sy = step["scale"]
            dir_x, dir_y = step["dir"]
            rot = 0
            if dir_x == 1: rot = 0
            elif dir_x == -1: rot = 180
            elif dir_y == 1: rot = 90
            elif dir_y == -1: rot = 270
            player_kf.append(f"      {pct:.2f}% {{ transform: translate({px}px, {py}px) rotate({rot}deg) scale({sx}, {sy}); opacity: 1; }}")
            
        player_kf_full = []
        if room_start_pct > 0:
            player_kf_full.append(f"      0.0% {{ transform: translate(0px, 0px) scale(0); opacity: 0; }}")
            player_kf_full.append(f"      {room_start_pct - 0.01:.2f}% {{ transform: translate(0px, 0px) scale(0); opacity: 0; }}")
        player_kf_full.extend(player_kf)
        if room_end_pct < 100:
            player_kf_full.append(f"      {room_end_pct:.2f}% {{ transform: translate(0px, 0px) scale(0); opacity: 0; }}")
            player_kf_full.append(f"      100.0% {{ transform: translate(0px, 0px) scale(0); opacity: 0; }}")
            
        kf_name = f"player-anim-{idx}"
        keyframe_animations.append(f"    @keyframes {kf_name} {{")
        keyframe_animations.extend(player_kf_full)
        keyframe_animations.append(f"    }}")
        styles.append(f"    #player-{idx} {{ animation: {kf_name} {total_duration:.2f}s infinite linear; }}")
        
        room_kf_name = f"room-fade-{idx}"
        room_kf = [
            f"    @keyframes {room_kf_name} {{",
            f"      0% {{ opacity: 0; pointer-events: none; }}",
        ]
        if room_start_pct > 0:
            room_kf.append(f"      {room_start_pct - 1.5:.2f}% {{ opacity: 0; pointer-events: none; }}")
        room_kf.append(f"      {room_start_pct:.2f}% {{ opacity: 1; pointer-events: auto; }}")
        room_kf.append(f"      {room_end_pct - 1.5:.2f}% {{ opacity: 1; pointer-events: auto; }}")
        room_kf.append(f"      {room_end_pct:.2f}% {{ opacity: 0; pointer-events: none; }}")
        room_kf.append(f"      100% {{ opacity: 0; pointer-events: none; }}")
        room_kf.append(f"    }}")
        keyframe_animations.extend(room_kf)
        styles.append(f"    #room-{idx} {{ animation: {room_kf_name} {total_duration:.2f}s infinite linear; }}")
        
        for (dc, dr), t_c in dots_collected.items():
            t_abs = room_start_time + t_c
            pct = (t_abs / total_duration) * 100.0
            
            dot_kf_name = f"dot-anim-{idx}-{dc}-{dr}"
            dot_kf = [
                f"    @keyframes {dot_kf_name} {{",
                f"      0% {{ transform: scale(1); opacity: 1; }}",
            ]
            if room_start_pct > 0:
                dot_kf.append(f"      {room_start_pct:.2f}% {{ transform: scale(1); opacity: 1; }}")
            dot_kf.append(f"      {pct:.2f}% {{ transform: scale(1); opacity: 1; }}")
            dot_kf.append(f"      {pct+1.0:.2f}% {{ transform: scale(0); opacity: 0; }}")
            dot_kf.append(f"      100% {{ transform: scale(0); opacity: 0; }}")
            dot_kf.append(f"    }}")
            
            keyframe_animations.extend(dot_kf)
            cx = dc * TILE + TILE / 2
            cy = dr * TILE + TILE / 2
            styles.append(f"    #dot-{idx}-{dc}-{dr} {{ animation: {dot_kf_name} {total_duration:.2f}s infinite linear; transform-origin: {cx}px {cy}px; }}")

    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" width="830" height="344" viewBox="0 0 830 344">')
    svg.append('  <defs>')
    svg.append('    <linearGradient id="buildingGrad" x1="0" y1="0" x2="0" y2="1">')
    svg.append('      <stop offset="0%" stop-color="#1e293b"/>')
    svg.append('      <stop offset="100%" stop-color="#0f172a"/>')
    svg.append('    </linearGradient>')
    svg.append('    <linearGradient id="parkGrad" x1="0" y1="0" x2="0" y2="1">')
    svg.append('      <stop offset="0%" stop-color="#14532d"/>')
    svg.append('      <stop offset="100%" stop-color="#052e16"/>')
    svg.append('    </linearGradient>')
    svg.append('    <linearGradient id="glassGrad" x1="0" y1="0" x2="0" y2="1">')
    svg.append('      <stop offset="0%" stop-color="#1e3a8a"/>')
    svg.append('      <stop offset="100%" stop-color="#0f172a"/>')
    svg.append('    </linearGradient>')
    svg.append('    <filter id="cityGlow" x="-50%" y="-50%" width="200%" height="200%">')
    svg.append('      <feGaussianBlur stdDeviation="2.5" result="blur"/>')
    svg.append('      <feMerge>')
    svg.append('        <feMergeNode in="blur"/>')
    svg.append('        <feMergeNode in="SourceGraphic"/>')
    svg.append('      </feMerge>')
    svg.append('    </filter>')
    svg.append('    <clipPath id="gridClip">')
    svg.append('      <rect x="0" y="0" width="792" height="264" rx="4"/>')
    svg.append('    </clipPath>')
    svg.append('  </defs>')
    
    svg.append('  <style>')
    svg.extend(styles)
    svg.extend(keyframe_animations)
    svg.append('  </style>')
    
    svg.append('  <rect width="830" height="344" fill="#070b19" rx="10" stroke="#1e293b" stroke-width="1.5"/>')
    svg.append('  <rect x="1" y="1" width="828" height="42" fill="#0f172a" rx="9" stroke="#1e293b" stroke-width="0.5"/>')
    svg.append('  <text x="30" y="27" font-size="13" fill="#f8fafc" font-family="monospace" font-weight="bold">🚗 Caminhos Procedurais — Navegação Urbana</text>')
    svg.append('  <rect x="660" y="14" width="140" height="20" rx="10" fill="#1e293b" stroke="#334155" stroke-width="0.8"/>')
    svg.append('  <circle cx="673" cy="24" r="3" fill="#10b981"/>')
    svg.append('  <text x="682" y="27" font-size="9" fill="#94a3b8" font-family="monospace">AUTOPLAY BOT</text>')
    
    svg.append('  <g transform="translate(19, 48)">')
    svg.append('    <rect width="792" height="264" fill="#080d1a" stroke="#1e293b" stroke-width="1.5" rx="4"/>')
    
    for idx, r_data in enumerate(rooms):
        grid = r_data["grid"]
        svg.append(f'    <g id="room-{idx}" clip-path="url(#gridClip)">')
        svg.append('      <g stroke="#131d31" stroke-width="0.8" stroke-dasharray="3,3">')
        for c in range(1, COLS):
            x = c * TILE
            svg.append(f'        <line x1="{x}" y1="0" x2="{x}" y2="264"/>')
        for r in range(1, ROWS):
            y = r * TILE
            svg.append(f'        <line x1="0" y1="{y}" x2="792" y2="{y}"/>')
        svg.append('      </g>')
        
        for r in range(ROWS):
            for c in range(COLS):
                val = grid[r][c]
                x = c * TILE
                y = r * TILE
                if val == 0:
                    block_type = (c * 13 + r * 37) % 4
                    if block_type == 0:
                        svg.append(f'      <rect x="{x}" y="{y}" width="24" height="24" fill="url(#buildingGrad)" stroke="#334155" stroke-width="0.8" rx="2"/>')
                        svg.append(f'      <rect x="{x+3}" y="{y+3}" width="18" height="18" fill="none" stroke="#1e293b" stroke-width="0.5"/>')
                        svg.append(f'      <rect x="{x+5}" y="{y+5}" width="5" height="5" fill="#475569" rx="1"/>')
                        svg.append(f'      <circle cx="{x+16}" cy="{y+8}" r="1" fill="#fef08a" opacity="0.8"/>')
                    elif block_type == 1:
                        svg.append(f'      <rect x="{x}" y="{y}" width="24" height="24" fill="url(#glassGrad)" stroke="#1d4ed8" stroke-width="0.6" rx="2"/>')
                        svg.append(f'      <line x1="{x+2}" y1="{y+12}" x2="{x+22}" y2="{y+12}" stroke="#2563eb" stroke-width="0.5" opacity="0.6"/>')
                        svg.append(f'      <circle cx="{x+12}" cy="{y+12}" r="2.5" fill="#0284c7" opacity="0.8"/>')
                    elif block_type == 2:
                        svg.append(f'      <rect x="{x}" y="{y}" width="24" height="24" fill="url(#parkGrad)" stroke="#166534" stroke-width="0.8" rx="2"/>')
                        svg.append(f'      <circle cx="{x+8}" cy="{y+12}" r="4" fill="#15803d"/>')
                        svg.append(f'      <circle cx="{x+16}" cy="{y+10}" r="3" fill="#22c55e"/>')
                    else:
                        svg.append(f'      <rect x="{x}" y="{y}" width="24" height="24" fill="url(#buildingGrad)" stroke="#475569" stroke-width="0.8" rx="2"/>')
                        svg.append(f'      <rect x="{x+4}" y="{y+4}" width="6" height="6" fill="#f59e0b" opacity="0.75" rx="0.5"/>')
                        svg.append(f'      <rect x="{x+14}" y="{y+14}" width="6" height="6" fill="#f59e0b" opacity="0.5" rx="0.5"/>')
                elif val == 1:
                    if (c, r) in r_data["coins"]:
                        svg.append(f'      <circle id="dot-{idx}-{c}-{r}" cx="{x+12}" cy="{y+12}" r="2.5" fill="#f59e0b"/>')
                        
        svg.append(f'      <g id="player-{idx}">')
        svg.append('        <polygon points="6,-4 22,-9 22,9 6,4" fill="#fef08a" opacity="0.35"/>')
        svg.append('        <rect x="-9" y="-6" width="18" height="12" rx="3" fill="#3b82f6" stroke="#1d4ed8" stroke-width="0.8"/>')
        svg.append('        <rect x="-4" y="-4" width="8" height="8" rx="2" fill="#0f172a"/>')
        svg.append('        <circle cx="0" cy="0" r="1.5" fill="#f59e0b"/>')
        svg.append('        <circle cx="8" cy="-3.5" r="1.2" fill="#fef08a"/>')
        svg.append('        <circle cx="8" cy="3.5" r="1.2" fill="#fef08a"/>')
        svg.append('        <rect x="-9" y="-4.5" width="1.2" height="2" fill="#ef4444"/>')
        svg.append('        <rect x="-9" y="2.5" width="1.2" height="2" fill="#ef4444"/>')
        svg.append('      </g>')
        svg.append('    </g>')
        
    svg.append('  </g>')
    
    svg.append('  <rect x="19" y="48" width="792" height="264" fill="none" stroke="#1e293b" stroke-width="1.5" rx="4"/>')
    svg.append('  <text x="415" y="331" text-anchor="middle" font-size="9" fill="#64748b" font-family="monospace">🏙️ Quarteirões Edificados • 🛣️ Malha Viária Procedural • 💡 Iluminação Urbana</text>')
    svg.append('</svg>')
    
    return "\n".join(svg)

def generate_tomb_svg():
    return generate_procedural_paths_svg()

def load_existing_data(output_dir):
    path = os.path.join(output_dir, "data.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    try:
        import subprocess
        out = subprocess.check_output(["git", "show", "origin/stats:data.json"], stderr=subprocess.DEVNULL)
        return json.loads(out.decode("utf-8"))
    except Exception:
        pass
    return {}

def main():
    today = datetime.date.today()
    output = "dist"
    os.makedirs(output, exist_ok=True)
    existing_all = load_existing_data(output)
    all_data = {}
    for i in range(6):
        m, y = today.month - i, today.year
        while m < 1:
            m += 12
            y -= 1
        key = f"{y}-{m:02d}"
        counts = commits_by_day(y, m)
        if key in existing_all and isinstance(existing_all[key], dict):
            for day_str, old_cnt in existing_all[key].items():
                try:
                    d_int = int(day_str)
                    counts[d_int] = max(counts.get(d_int, 0), old_cnt)
                except ValueError:
                    pass
        all_data[key] = counts
        print(f"  {key}: {sum(counts.values())} commits")
    
    with open(f"{output}/data.json", "w") as f:
        json.dump(all_data, f)
        
    cur = f"{today.year}-{today.month:02d}"
    with open(f"{output}/skyline_v3.svg", "w", encoding="utf-8") as f:
        f.write(generate_svg(today.year, today.month, all_data.get(cur, {})))
        
    procedural_svg = generate_procedural_paths_svg()
    with open(f"{output}/tomb_v1.svg", "w", encoding="utf-8") as f:
        f.write(procedural_svg)
    with open(f"{output}/caminhos_v1.svg", "w", encoding="utf-8") as f:
        f.write(procedural_svg)
    with open(f"{output}/caminhos_v2.svg", "w", encoding="utf-8") as f:
        f.write(procedural_svg)
        
    with open(f"{output}/index.html", "w", encoding="utf-8") as f:
        f.write(generate_html(all_data))
        
    print("Concluído!")

if __name__ == "__main__":
    main()
