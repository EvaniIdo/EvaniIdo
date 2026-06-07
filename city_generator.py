import os
import json
import random
import datetime
import calendar
import urllib.request
import urllib.error

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER  = os.environ.get("GITHUB_USER", "EvaniIdo")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

def gh_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError:
        return []

def fetch_repos():
    repos, page = [], 1
    while True:
        chunk = gh_get(f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&page={page}&type=owner")
        if not chunk: break
        repos += [r["full_name"] for r in chunk]
        if len(chunk) < 100: break
        page += 1
    return repos

def commits_by_day(year, month):
    last_day = calendar.monthrange(year, month)[1]
    since = f"{year}-{month:02d}-01T00:00:00Z"
    until = f"{year}-{month:02d}-{last_day}T23:59:59Z"
    counts = {d: 0 for d in range(1, last_day + 1)}
    for repo in fetch_repos():
        url = (f"https://api.github.com/repos/{repo}/commits"
               f"?since={since}&until={until}&per_page=100")
        items = gh_get(url)
        if not isinstance(items, list): continue
        for item in items:
            try:
                d = int(item["commit"]["author"]["date"][8:10])
                if d in counts: counts[d] += 1
            except (KeyError, ValueError):
                pass
    return counts

# ── Isometric SVG generation ──

def adjust_color(hex_color, amount):
    # simple brightness adjustment
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r = max(0, min(255, r + amount))
    g = max(0, min(255, g + amount))
    b = max(0, min(255, b + amount))
    return f"#{r:02x}{g:02x}{b:02x}"

def draw_iso_block(cx, cy, w, h, base_color, add_windows=False):
    c_left = adjust_color(base_color, -30)
    c_right = adjust_color(base_color, -60)
    c_top = adjust_color(base_color, 20)
    
    svg = []
    
    # Left face
    svg.append(f'<polygon points="{cx-w},{cy-w/2} {cx},{cy} {cx},{cy-h} {cx-w},{cy-w/2-h}" fill="{c_left}" stroke="#111" stroke-width="0.5"/>')
    # Right face
    svg.append(f'<polygon points="{cx},{cy} {cx+w},{cy-w/2} {cx+w},{cy-w/2-h} {cx},{cy-h}" fill="{c_right}" stroke="#111" stroke-width="0.5"/>')
    # Top face
    svg.append(f'<polygon points="{cx},{cy-h} {cx-w},{cy-w/2-h} {cx},{cy-w-h} {cx+w},{cy-w/2-h}" fill="{c_top}" stroke="#111" stroke-width="0.5"/>')
    
    if add_windows and h > 10:
        win_color = "#fef08a"
        for wy in range(10, int(h)-5, 15):
            # left windows
            svg.append(f'<polygon points="{cx-w+4},{cy-w/2-wy} {cx-4},{cy-wy+w/2-4} {cx-4},{cy-wy+w/2-4-6} {cx-w+4},{cy-w/2-wy-6}" fill="{win_color}" opacity="0.8"/>')
            # right windows
            svg.append(f'<polygon points="{cx+4},{cy-wy+w/2-4} {cx+w-4},{cy-w/2-wy} {cx+w-4},{cy-w/2-wy-6} {cx+4},{cy-wy+w/2-4-6}" fill="{win_color}" opacity="0.8"/>')
            
    return "\n".join(svg)

def draw_park(cx, cy, w):
    c_top = "#166534"
    svg = []
    # Base
    svg.append(f'<polygon points="{cx},{cy} {cx-w},{cy-w/2} {cx},{cy-w} {cx+w},{cy-w/2}" fill="{c_top}" stroke="#111" stroke-width="0.5"/>')
    # Tree trunk
    svg.append(f'<polygon points="{cx-2},{cy-w/2} {cx+2},{cy-w/2+2} {cx+2},{cy-w/2-8} {cx-2},{cy-w/2-10}" fill="#854d0e"/>')
    # Tree leaves (simple sphere-like)
    svg.append(f'<circle cx="{cx}" cy="{cy-w/2-10}" r="8" fill="#15803d" stroke="#111" stroke-width="0.5"/>')
    return "\n".join(svg)

def draw_empty(cx, cy, w):
    c_top = "#374151"
    return f'<polygon points="{cx},{cy} {cx-w},{cy-w/2} {cx},{cy-w} {cx+w},{cy-w/2}" fill="{c_top}" stroke="#111" stroke-width="0.5"/>'

def generate_svg(year, month, counts):
    last_day = calendar.monthrange(year, month)[1]
    today = datetime.date.today()
    mname = datetime.date(year, month, 1).strftime("%B %Y")
    
    W, H = 800, 600
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    svg.append(f'<rect width="{W}" height="{H}" fill="#0f172a"/>')
    
    svg.append(f'<text x="{W//2}" y="40" text-anchor="middle" font-size="20" fill="#e5e7eb" font-family="sans-serif" font-weight="bold">&#x1F4C5; {mname}</text>')
    
    tile_w = 40
    offset_x = W // 2
    offset_y = 250
    
    # We will lay out the month as a calendar grid
    # col = day of week (0 to 6)
    # row = week of month
    
    start_weekday = calendar.monthrange(year, month)[0] # 0 = Monday, 6 = Sunday
    
    blocks = [] # Store elements to sort by depth (y)
    
    for d in range(1, last_day + 1):
        idx = start_weekday + d - 1
        col = idx % 7
        row = idx // 7
        
        cx = offset_x + (col - row) * tile_w
        cy = offset_y + (col + row) * (tile_w / 2)
        
        commits = counts.get(d, 0)
        cur = datetime.date(year, month, d)
        
        # Calculate depth for sorting (Painter's algorithm)
        depth = col + row
        
        content = ""
        label = f'<text x="{cx}" y="{cy + 15}" text-anchor="middle" font-size="10" fill="#9ca3af" font-family="sans-serif">{d}</text>'
        
        if cur > today:
            content = draw_empty(cx, cy, tile_w)
        elif commits == 0:
            content = draw_empty(cx, cy, tile_w)
        elif commits == 1:
            content = draw_park(cx, cy, tile_w)
        else:
            # Building height based on commits
            h = min(200, commits * 10 + 10)
            
            # Color based on commits
            if commits <= 3: base_color = "#3b82f6"
            elif commits <= 6: base_color = "#8b5cf6"
            elif commits <= 10: base_color = "#ec4899"
            else: base_color = "#f59e0b"
            
            content = draw_iso_block(cx, cy, tile_w, h, base_color, add_windows=(commits>2))
            # Floating commit badge
            label += f'<text x="{cx}" y="{cy - h - 15}" text-anchor="middle" font-size="12" fill="#fff" font-weight="bold" font-family="sans-serif">{commits}</text>'
            
        blocks.append((depth, content + "\n" + label))
        
    # Sort blocks by depth (back to front)
    blocks.sort(key=lambda x: x[0])
    for _, content in blocks:
        svg.append(content)
        
    # Legend
    svg.append('<g transform="translate(20, 500)">')
    svg.append('<text x="0" y="0" fill="#fff" font-family="sans-serif" font-size="14" font-weight="bold">Legenda:</text>')
    
    legend_items = [
        ("#374151", "0 commits / Futuro"),
        ("#166534", "1 commit (Praça)"),
        ("#3b82f6", "2-3 commits"),
        ("#8b5cf6", "4-6 commits"),
        ("#ec4899", "7-10 commits"),
        ("#f59e0b", "11+ commits")
    ]
    
    for i, (color, text) in enumerate(legend_items):
        svg.append(f'<rect x="0" y="{15 + i*20}" width="15" height="15" fill="{color}" stroke="#111" stroke-width="1"/>')
        svg.append(f'<text x="25" y="{27 + i*20}" fill="#9ca3af" font-family="sans-serif" font-size="12">{text}</text>')
    
    svg.append('</g>')
        
    svg.append("</svg>")
    return "\n".join(svg)

def generate_html(all_data):
    data_json = json.dumps(all_data)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>GitHub City</title>
<style>
body {{ background: #0f172a; color: #fff; font-family: sans-serif; text-align: center; margin: 0; padding: 20px; }}
select {{ padding: 10px; font-size: 16px; margin: 20px; border-radius: 5px; background: #1e293b; color: #fff; border: 1px solid #475569; }}
.container {{ display: flex; justify-content: center; }}
</style>
</head>
<body>
<h1>&#x1F3D9;&#xFE0F; GitHub City Isometrica</h1>
<select id="monthSel"></select>
<div class="container" id="city-container"></div>
<script>
const DATA = {data_json};

function renderSVG(year, month, counts) {{
    const lastDay = new Date(year, month, 0).getDate();
    const today = new Date();
    
    const W = 800, H = 600;
    let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${{W}}" height="${{H}}" viewBox="0 0 ${{W}} ${{H}}">`;
    svg += `<rect width="${{W}}" height="${{H}}" fill="#0f172a"/>`;
    
    const mNames=["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
    svg += `<text x="${{W/2}}" y="40" text-anchor="middle" font-size="20" fill="#e5e7eb" font-family="sans-serif" font-weight="bold">&#x1F4C5; ${{mNames[month-1]}} ${{year}}</text>`;
    
    const tileW = 40;
    const offsetX = W / 2;
    const offsetY = 250;
    
    const startWeekday = new Date(year, month - 1, 1).getDay(); // 0 = Sun
    const adjustedStart = startWeekday === 0 ? 6 : startWeekday - 1; // 0 = Mon
    
    let blocks = [];
    
    for (let d = 1; d <= lastDay; d++) {{
        const idx = adjustedStart + d - 1;
        const col = idx % 7;
        const row = Math.floor(idx / 7);
        
        const cx = offsetX + (col - row) * tileW;
        const cy = offsetY + (col + row) * (tileW / 2);
        
        const commits = counts[d] || 0;
        const curDate = new Date(year, month - 1, d);
        const depth = col + row;
        
        let content = "";
        let label = `<text x="${{cx}}" y="${{cy + 15}}" text-anchor="middle" font-size="10" fill="#9ca3af" font-family="sans-serif">${{d}}</text>`;
        
        if (curDate > today || commits === 0) {{
            content = `<polygon points="${{cx}},${{cy}} ${{cx-tileW}},${{cy-tileW/2}} ${{cx}},${{cy-tileW}} ${{cx+tileW}},${{cy-tileW/2}}" fill="#374151" stroke="#111" stroke-width="0.5"/>`;
        }} else if (commits === 1) {{
            content = `<polygon points="${{cx}},${{cy}} ${{cx-tileW}},${{cy-tileW/2}} ${{cx}},${{cy-tileW}} ${{cx+tileW}},${{cy-tileW/2}}" fill="#166534" stroke="#111" stroke-width="0.5"/>`;
            content += `<polygon points="${{cx-2}},${{cy-tileW/2}} ${{cx+2}},${{cy-tileW/2+2}} ${{cx+2}},${{cy-tileW/2-8}} ${{cx-2}},${{cy-tileW/2-10}}" fill="#854d0e"/>`;
            content += `<circle cx="${{cx}}" cy="${{cy-tileW/2-10}}" r="8" fill="#15803d" stroke="#111" stroke-width="0.5"/>`;
        }} else {{
            const h = Math.min(200, commits * 10 + 10);
            let baseColor;
            if (commits <= 3) baseColor = "#3b82f6";
            else if (commits <= 6) baseColor = "#8b5cf6";
            else if (commits <= 10) baseColor = "#ec4899";
            else baseColor = "#f59e0b";
            
            // very simple shading
            content = `<polygon points="${{cx-tileW}},${{cy-tileW/2}} ${{cx}},${{cy}} ${{cx}},${{cy-h}} ${{cx-tileW}},${{cy-tileW/2-h}}" fill="${{baseColor}}" opacity="0.8" stroke="#111" stroke-width="0.5"/>`;
            content += `<polygon points="${{cx}},${{cy}} ${{cx+tileW}},${{cy-tileW/2}} ${{cx+tileW}},${{cy-tileW/2-h}} ${{cx}},${{cy-h}}" fill="${{baseColor}}" opacity="0.6" stroke="#111" stroke-width="0.5"/>`;
            content += `<polygon points="${{cx}},${{cy-h}} ${{cx-tileW}},${{cy-tileW/2-h}} ${{cx}},${{cy-tileW-h}} ${{cx+tileW}},${{cy-tileW/2-h}}" fill="${{baseColor}}" stroke="#111" stroke-width="0.5"/>`;
            
            label += `<text x="${{cx}}" y="${{cy - h - 15}}" text-anchor="middle" font-size="12" fill="#fff" font-weight="bold" font-family="sans-serif">${{commits}}</text>`;
        }}
        
        blocks.push({{ depth, svg: content + "\\n" + label }});
    }}
    
    blocks.sort((a, b) => a.depth - b.depth);
    blocks.forEach(b => svg += b.svg);
    
    // Legend
    svg += '<g transform="translate(20, 500)">';
    svg += '<text x="0" y="0" fill="#fff" font-family="sans-serif" font-size="14" font-weight="bold">Legenda:</text>';
    const legendItems = [
        ["#374151", "0 commits / Futuro"],
        ["#166534", "1 commit (Praça)"],
        ["#3b82f6", "2-3 commits"],
        ["#8b5cf6", "4-6 commits"],
        ["#ec4899", "7-10 commits"],
        ["#f59e0b", "11+ commits"]
    ];
    legendItems.forEach((item, i) => {{
        svg += `<rect x="0" y="${{15 + i*20}}" width="15" height="15" fill="${{item[0]}}" stroke="#111" stroke-width="1"/>`;
        svg += `<text x="25" y="${{27 + i*20}}" fill="#9ca3af" font-family="sans-serif" font-size="12">${{item[1]}}</text>`;
    }});
    svg += '</g>';
    
    svg += `</svg>`;
    return svg;
}}

const sel = document.getElementById("monthSel");
const keys = Object.keys(DATA).sort().reverse();
keys.forEach(k => {{
    const opt = document.createElement("option");
    opt.value = k; opt.textContent = k;
    sel.appendChild(opt);
}});

sel.addEventListener("change", () => {{
    const [y, m] = sel.value.split("-").map(Number);
    document.getElementById("city-container").innerHTML = renderSVG(y, m, DATA[sel.value] || {{}});
}});

if (keys.length > 0) {{
    sel.value = keys[0];
    sel.dispatchEvent(new Event("change"));
}}

</script>
</body>
</html>"""

def main():
    today = datetime.date.today()
    output = "dist"
    os.makedirs(output, exist_ok=True)
    all_data = {}
    for i in range(6):
        m, y = today.month - i, today.year
        while m < 1:
            m += 12
            y -= 1
        key = f"{y}-{m:02d}"
        counts = commits_by_day(y, m)
        all_data[key] = counts
        print(f"  {key}: {sum(counts.values())} commits")
    
    with open(f"{output}/data.json", "w") as f:
        json.dump(all_data, f)
        
    cur = f"{today.year}-{today.month:02d}"
    with open(f"{output}/city.svg", "w", encoding="utf-8") as f:
        f.write(generate_svg(today.year, today.month, all_data.get(cur, {})))
        
    with open(f"{output}/index.html", "w", encoding="utf-8") as f:
        f.write(generate_html(all_data))
        
    print("Done!")

if __name__ == "__main__":
    main()
