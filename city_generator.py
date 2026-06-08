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

# ── Gerador de SVG do Skyline 2D ──

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
    if commits == 0: return 0
    if commits == 1: return 0
    if commits <= 3: return 60
    if commits <= 6: return 110
    if commits <= 10: return 160
    if commits <= 15: return 210
    return 310

def draw_sky(o, svg_w):
    o.append(f'<defs>'
             f'<linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0%" stop-color="#070b19"/>'
             f'<stop offset="60%" stop-color="#10172a"/>'
             f'<stop offset="100%" stop-color="#1e1b4b"/>'
             f'</linearGradient>'
             f'</defs>')
    o.append(f'<rect width="{svg_w}" height="{H}" fill="url(#skyGrad)"/>')
    # estrelas
    rng = random.Random(42)
    for _ in range(90):
        sx, sy = rng.randint(0, svg_w), rng.randint(0, GROUND_Y - 20)
        op, r = round(rng.uniform(0.2, 0.9), 2), round(rng.uniform(0.5, 1.5), 1)
        o.append(f'<circle cx="{sx}" cy="{sy}" r="{r}" fill="#ffffff" opacity="{op}"/>')

def draw_street(o, svg_w):
    # calçada
    o.append(f'<rect x="0" y="{GROUND_Y}" width="{svg_w}" height="8" fill="#475569"/>')
    # rua
    o.append(f'<rect x="0" y="{GROUND_Y+8}" width="{svg_w}" height="28" fill="#1e293b"/>')
    # faixas da rua
    o.append(f'<line x1="0" y1="{GROUND_Y+22}" x2="{svg_w}" y2="{GROUND_Y+22}" stroke="#e2e8f0" stroke-width="2" stroke-dasharray="12,12"/>')

def draw_park(o, x):
    # grama
    o.append(f'<rect x="{x}" y="{GROUND_Y-6}" width="{LOT_W}" height="6" fill="#15803d" rx="1"/>')
    # banco
    bx = x + 3
    o.append(f'<rect x="{bx}" y="{GROUND_Y-9}" width="6" height="3" fill="#b45309"/>')
    o.append(f'<line x1="{bx}" y1="{GROUND_Y-9}" x2="{bx}" y2="{GROUND_Y-6}" stroke="#78350f" stroke-width="1"/>')
    o.append(f'<line x1="{bx+6}" y1="{GROUND_Y-9}" x2="{bx+6}" y2="{GROUND_Y-6}" stroke="#78350f" stroke-width="1"/>')
    # árvore
    tx = x + 18
    o.append(f'<rect x="{tx-1}" y="{GROUND_Y-16}" width="2" height="10" fill="#78350f"/>')
    o.append(f'<circle cx="{tx}" cy="{GROUND_Y-19}" r="7" fill="#16a34a"/>')
    o.append(f'<circle cx="{tx-3}" cy="{GROUND_Y-22}" r="5" fill="#22c55e"/>')

def draw_construction(o, x):
    # andaimes/guindastes para dias futuros
    o.append(f'<rect x="{x}" y="{GROUND_Y-40}" width="{LOT_W}" height="40" fill="none" stroke="#475569" stroke-width="1" stroke-dasharray="3,3" rx="1"/>')
    # braço do guindaste
    mx = x + LOT_W // 2
    o.append(f'<line x1="{mx}" y1="{GROUND_Y-40}" x2="{mx}" y2="{GROUND_Y-52}" stroke="#64748b" stroke-width="1.5"/>')
    o.append(f'<line x1="{mx}" y1="{GROUND_Y-52}" x2="{mx+10}" y2="{GROUND_Y-52}" stroke="#64748b" stroke-width="1.5"/>')

def draw_road_lamp(o, x):
    # poste de luz
    lx = x + LOT_W // 2
    o.append(f'<line x1="{lx}" y1="{GROUND_Y}" x2="{lx}" y2="{GROUND_Y-24}" stroke="#64748b" stroke-width="1.5"/>')
    o.append(f'<path d="M {lx} {GROUND_Y-24} Q {lx+5} {GROUND_Y-26} {lx+8} {GROUND_Y-22}" fill="none" stroke="#64748b" stroke-width="1.5"/>')
    o.append(f'<circle cx="{lx+8}" cy="{GROUND_Y-21}" r="2" fill="#fef08a"/>')

def draw_detailed_building(o, x, commits, day_seed):
    h = building_height(commits)
    y = GROUND_Y - h
    w = LOT_W
    
    # 4 estilos arquitetônicos distintos com base na seed do dia
    style = day_seed % 4
    
    # Paletas de cores base
    palettes = [
        ["#3b82f6", "#2563eb", "#1d4ed8"],  # Vidro Moderno Azul
        ["#b45309", "#92400e", "#78350f"],  # Tijolo Clássico Laranja
        ["#8b5cf6", "#7c3aed", "#6d28d9"],  # Alta Tecnologia Roxo
        ["#0d9488", "#0f766e", "#115e59"]   # Elegante Verde Água
    ]
    colors = palettes[style]
    
    # Corpo principal do prédio com gradiente vertical
    o.append(f'<defs>'
             f'<linearGradient id="grad_{day_seed}" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0%" stop-color="{colors[0]}"/>'
             f'<stop offset="100%" stop-color="{colors[2]}"/>'
             f'</linearGradient>'
             f'</defs>')
    
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#grad_{day_seed})" rx="1"/>')
    
    # Sombra lateral 3D
    o.append(f'<rect x="{x+w-4}" y="{y}" width="4" height="{h}" fill="#000000" opacity="0.2"/>')
    
    # Portas
    o.append(f'<rect x="{x+w//2-3}" y="{GROUND_Y-8}" width="6" height="8" fill="#1e293b"/>')
    o.append(f'<rect x="{x+w//2-2}" y="{GROUND_Y-7}" width="2" height="7" fill="#fef08a" opacity="0.8"/>')
    
    # Janelas
    win_color = "#fef08a"
    rng = random.Random(day_seed + 100)
    
    if style == 0:
        # Estilo 0: Fachada de vidro com linhas verticais
        cols = 3
        rows = max(1, (h - 15) // 10)
        ww, wh = 4, 6
        for r in range(rows):
            for c in range(cols):
                if rng.random() < 0.75:
                    wx = x + 3 + c * 7
                    wy = y + 8 + r * 9
                    o.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="{win_color}" opacity="0.9"/>')
        # antena/espira
        o.append(f'<line x1="{x+w//2}" y1="{y}" x2="{x+w//2}" y2="{y-15}" stroke="#94a3b8" stroke-width="1.5"/>')
        o.append(f'<circle cx="{x+w//2}" cy="{y-15}" r="2" fill="#ef4444"/>')
        
    elif style == 1:
        # Estilo 1: Estrutura de tijolos com janelas em arco
        cols = 2
        rows = max(1, (h - 15) // 12)
        ww, wh = 6, 8
        for r in range(rows):
            for c in range(cols):
                if rng.random() < 0.8:
                    wx = x + 4 + c * 11
                    wy = y + 8 + r * 11
                    # arco
                    o.append(f'<path d="M {wx} {wy+wh} L {wx} {wy+3} A {ww/2} {ww/2} 0 0 1 {wx+ww} {wy+3} L {wx+ww} {wy+wh} Z" fill="{win_color}" opacity="0.9"/>')
        # Telhado triangular
        o.append(f'<polygon points="{x-2},{y} {x+w//2},{y-10} {x+w+2},{y}" fill="{colors[1]}" stroke="#1e293b" stroke-width="1"/>')
        
    elif style == 2:
        # Estilo 2: Painéis de grade de alta tecnologia
        cols = 2
        rows = max(1, (h - 15) // 14)
        ww, wh = 8, 10
        for r in range(rows):
            for c in range(cols):
                if rng.random() < 0.7:
                    wx = x + 4 + c * 10
                    wy = y + 8 + r * 13
                    o.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="{win_color}" opacity="0.95"/>')
                    o.append(f'<line x1="{wx}" y1="{wy+wh//2}" x2="{wx+ww}" y2="{wy+wh//2}" stroke="{colors[2]}" stroke-width="0.5"/>')
        # Caixa d'água no telhado
        o.append(f'<rect x="{x+4}" y="{y-8}" width="8" height="8" fill="#64748b" rx="1"/>')
        o.append(f'<line x1="{x+5}" y1="{y}" x2="{x+5}" y2="{y-8}" stroke="#475569" stroke-width="1"/>')
        o.append(f'<line x1="{x+11}" y1="{y}" x2="{x+11}" y2="{y-8}" stroke="#475569" stroke-width="1"/>')
        
    else:
        # Estilo 3: Torre clássica com sacadas
        cols = 2
        rows = max(1, (h - 15) // 15)
        ww, wh = 6, 8
        for r in range(rows):
            for c in range(cols):
                wx = x + 4 + c * 11
                wy = y + 8 + r * 14
                if rng.random() < 0.8:
                    o.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="{win_color}" opacity="0.9"/>')
                # borda da sacada
                o.append(f'<rect x="{wx-1}" y="{wy+wh}" width="{ww+2}" height="2" fill="#cbd5e1"/>')
        # Telhado em cúpula
        o.append(f'<path d="M {x+2} {y} A {w//2-2} {w//2-2} 0 0 1 {x+w-2} {y} Z" fill="{colors[1]}"/>')

def generate_svg(year, month, counts):
    last_day = calendar.monthrange(year, month)[1]
    today = datetime.date.today()
    mname = datetime.date(year, month, 1).strftime("%B %Y")
    
    svg_w = ML * 2 + last_day * (LOT_W + GAP) - GAP
    svg_w = max(W, svg_w)
    
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{H}" viewBox="0 0 {svg_w} {H}">')
    
    draw_sky(o, svg_w)
    
    # Título
    o.append(f'<text x="{svg_w//2}" y="32" text-anchor="middle" font-size="16" fill="#f8fafc" font-family="{FONT}" font-weight="bold">&#x1F3D9;&#xFE0F; GitHub City Skyline — {mname}</text>')
    
    draw_street(o, svg_w)
    
    for d in range(1, last_day + 1):
        x = ML + (d - 1) * (LOT_W + GAP)
        commits = counts.get(d, 0)
        cur = datetime.date(year, month, d)
        
        is_today = cur == today
        is_future = cur > today
        day_seed = (year * 100 + month) * 100 + d
        
        # Início do grupo com tooltip de hover
        o.append(f'<g>')
        o.append(f'<title>Dia {d}: {commits} {"commit" if commits == 1 else "commits"}</title>')
        
        # Linha de grade para alinhamento dos dias
        o.append(f'<line x1="{x + LOT_W//2}" y1="50" x2="{x + LOT_W//2}" y2="{GROUND_Y}" stroke="#334155" stroke-width="0.5" stroke-dasharray="2,4"/>')
        
        if is_future:
            draw_construction(o, x)
        elif commits == 0:
            # Talvez colocar um poste de luz às vezes para adicionar detalhes
            if day_seed % 5 == 0:
                draw_road_lamp(o, x)
        elif commits == 1:
            draw_park(o, x)
        else:
            draw_detailed_building(o, x, commits, day_seed)
            # Emblema de commits flutuante
            h = building_height(commits)
            b_width = 14
            b_height = 10
            by = 42 if h >= 310 else (GROUND_Y - h - 16)
            o.append(f'<rect x="{x + LOT_W//2 - b_width//2}" y="{by}" width="{b_width}" height="{b_height}" fill="#f59e0b" rx="2"/>')
            o.append(f'<text x="{x + LOT_W//2}" y="{by + 8}" text-anchor="middle" font-size="8" fill="#0f172a" font-weight="bold" font-family="{FONT}">{commits}</text>')
        
        # Etiquetas dos Dias
        lbl_color = "#f59e0b" if is_today else "#94a3b8"
        font_w = "bold" if is_today else "normal"
        o.append(f'<text x="{x + LOT_W//2}" y="{GROUND_Y + 20}" text-anchor="middle" font-size="10" fill="{lbl_color}" font-weight="{font_w}" font-family="{FONT}">{d}</text>')
        
        if is_today:
            # Apontador de destaque para o dia de hoje
            o.append(f'<polygon points="{x+LOT_W//2-4},{GROUND_Y+25} {x+LOT_W//2+4},{GROUND_Y+25} {x+LOT_W//2},{GROUND_Y+30}" fill="#f59e0b"/>')

        o.append(f'</g>')
    
    # Legenda
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
    
    // Céu
    svg += `<defs>
      <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#070b19"/>
        <stop offset="60%" stop-color="#10172a"/>
        <stop offset="100%" stop-color="#1e1b4b"/>
      </linearGradient>
    </defs>`;
    svg += `<rect width="${{svgW}}" height="${{H}}" fill="url(#skyGrad)"/>`;
    
    // Estrelas
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
    
    // Título
    svg += `<text x="${{svgW/2}}" y="32" text-anchor="middle" font-size="16" fill="#f8fafc" font-family="monospace" font-weight="bold">&#x1F3D9;&#xFE0F; GitHub City Skyline — ${{mname}}</text>`;
    
    // Calçada e Rua
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
        
        // Início do grupo com tooltip de hover
        svg += `<g>`;
        svg += `<title>Dia ${{d}}: ${{commits}} ${{commits === 1 ? 'commit' : 'commits'}}</title>`;
        
        // Linha de Alinhamento
        svg += `<line x1="${{x + LOT_W/2}}" y1="50" x2="${{x + LOT_W/2}}" y2="${{GROUND_Y}}" stroke="#334155" stroke-width="0.5" stroke-dasharray="2,4"/>`;
        
        if (isFuture) {{
            // Andaimes de construção
            svg += `<rect x="${{x}}" y="${{GROUND_Y-40}}" width="${{LOT_W}}" height="40" fill="none" stroke="#475569" stroke-width="1" stroke-dasharray="3,3" rx="1"/>`;
            const mx = x + LOT_W / 2;
            svg += `<line x1="${{mx}}" y1="${{GROUND_Y-40}}" x2="${{mx}}" y2="${{GROUND_Y-52}}" stroke="#64748b" stroke-width="1.5"/>`;
            svg += `<line x1="${{mx}}" y1="${{GROUND_Y-52}}" x2="${{mx+10}}" y2="${{GROUND_Y-52}}" stroke="#64748b" stroke-width="1.5"/>`;
        }} else if (commits === 0) {{
            // Poste de luz
            if (daySeed % 5 === 0) {{
                const lx = x + LOT_W / 2;
                svg += `<line x1="${{lx}}" y1="${{GROUND_Y}}" x2="${{lx}}" y2="${{GROUND_Y-24}}" stroke="#64748b" stroke-width="1.5"/>`;
                svg += `<path d="M ${{lx}} ${{GROUND_Y-24}} Q ${{lx+5}} ${{GROUND_Y-26}} ${{lx+8}} ${{GROUND_Y-22}}" fill="none" stroke="#64748b" stroke-width="1.5"/>`;
                svg += `<circle cx="${{lx+8}}" cy="${{GROUND_Y-21}}" r="2" fill="#fef08a"/>`;
            }}
        }} else if (commits === 1) {{
            // Praça
            svg += `<rect x="${{x}}" y="${{GROUND_Y-6}}" width="${{LOT_W}}" height="6" fill="#15803d" rx="1"/>`;
            svg += `<rect x="${{x+3}}" y="${{GROUND_Y-9}}" width="6" height="3" fill="#b45309"/>`;
            svg += `<line x1="${{x+3}}" y1="${{GROUND_Y-9}}" x2="${{x+3}}" y2="${{GROUND_Y-6}}" stroke="#78350f" stroke-width="1"/>`;
            svg += `<line x1="${{x+9}}" y1="${{GROUND_Y-9}}" x2="${{x+9}}" y2="${{GROUND_Y-6}}" stroke="#78350f" stroke-width="1"/>`;
            svg += `<rect x="${{x+17}}" y="${{GROUND_Y-16}}" width="2" height="10" fill="#78350f"/>`;
            svg += `<circle cx="${{x+18}}" cy="${{GROUND_Y-19}}" r="7" fill="#16a34a"/>`;
            svg += `<circle cx="${{x+15}}" cy="${{GROUND_Y-22}}" r="5" fill="#22c55e"/>`;
        }} else {{
            // Prédio
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
            // Sombra lateral
            svg += `<rect x="${{x+LOT_W-4}}" y="${{yPos}}" width="4" height="${{h}}" fill="#000000" opacity="0.2"/>`;
            // Portas
            svg += `<rect x="${{x+LOT_W/2-3}}" y="${{GROUND_Y-8}}" width="6" height="8" fill="#1e293b"/>`;
            svg += `<rect x="${{x+LOT_W/2-2}}" y="${{GROUND_Y-7}}" width="2" height="7" fill="#fef08a" opacity="0.8"/>`;
            
            // Janelas
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
            
            // Emblema de commits flutuante
            const bWidth = 14, bHeight = 10;
            const by = h >= 310 ? 42 : yPos - 16;
            svg += `<rect x="${{x + LOT_W/2 - bWidth/2}}" y="${{by}}" width="${{bWidth}}" height="${{bHeight}}" fill="#f59e0b" rx="2"/>`;
            svg += `<text x="${{x + LOT_W/2}}" y="${{by + 8}}" text-anchor="middle" font-size="8" fill="#0f172a" font-weight="bold" font-family="monospace">${{commits}}</text>`;
        }}
        
        // Etiqueta do Dia
        let lblColor = isToday ? "#f59e0b" : "#94a3b8";
        let fontW = isToday ? "bold" : "normal";
        svg += `<text x="${{x + LOT_W/2}}" y="${{GROUND_Y+20}}" text-anchor="middle" font-size="10" fill="${{lblColor}}" font-weight="${{fontW}}" font-family="monospace">${{d}}</text>`;
        
        if (isToday) {{
            svg += `<polygon points="${{x+LOT_W/2-4}},${{GROUND_Y+25}} ${{x+LOT_W/2+4}},${{GROUND_Y+25}} ${{x+LOT_W/2}},${{GROUND_Y+30}}" fill="#f59e0b"/>`;
        }}
        
        svg += `</g>`;
    }}

    
    // Legenda
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

def generate_tomb_svg():
    TILE = 24
    COLS = 9
    ROWS = 13

    # ── Slide physics ────────────────────────────────────────────────────────
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
        """All cells crossed (not including start) when sliding from (cx,cy) to (tx,ty)."""
        dx = 0 if tx == cx else (1 if tx > cx else -1)
        dy = 0 if ty == cy else (1 if ty > cy else -1)
        cells, x, y = [], cx, cy
        while (x, y) != (tx, ty):
            x += dx; y += dy
            cells.append((x, y))
        return cells

    # ── Build full slide graph from a starting cell ───────────────────────────
    def build_slide_graph(grid, start_x, start_y):
        queue = [(start_x, start_y)]
        dps = {(start_x, start_y)}
        adj = {}          # dp -> list of (dest_dp, [cells crossed])
        while queue:
            cx, cy = queue.pop(0)
            adj[(cx, cy)] = []
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                tx, ty = slide_dest(grid, cx, cy, dx, dy)
                if (tx, ty) != (cx, cy):
                    adj[(cx, cy)].append(((tx, ty), slide_cells(cx, cy, tx, ty)))
                    if (tx, ty) not in dps:
                        dps.add((tx, ty))
                        queue.append((tx, ty))
        return dps, adj

    # ── Check every dp can reach every other dp (strong connectivity) ─────────
    def is_strongly_connected(adj, dps):
        if len(dps) < 2:
            return True
        start = next(iter(dps))
        # forward BFS
        seen = {start}
        q = [start]
        while q:
            cur = q.pop()
            for dest, _ in adj.get(cur, []):
                if dest not in seen:
                    seen.add(dest); q.append(dest)
        if seen != dps:
            return False
        # reverse BFS (follow edges backwards)
        rev = {dp: [] for dp in dps}
        for src, edges in adj.items():
            for dest, cells in edges:
                rev[dest].append(src)
        seen2 = {start}
        q = [start]
        while q:
            cur = q.pop()
            for prev in rev.get(cur, []):
                if prev not in seen2:
                    seen2.add(prev); q.append(prev)
        return seen2 == dps

    # ── Prim's maze carving (all walls → carve corridors) ────────────────────
    # Grid coords are at 2x scale internally so walls sit between cells.
    # Then we downsample to COLS×ROWS.
    # But COLS=9 ROWS=13 are both odd, perfect for a 2-scale maze.
    def carve_maze():
        # Work at (COLS)×(ROWS) where border is always wall.
        # Inner cells: odd coords are "rooms", even coords are "walls between rooms".
        # (COLS=9, ROWS=13 → 4×6 room cells inside)
        W, H = COLS, ROWS
        g = [[0]*W for _ in range(H)]  # start all walls

        # Mark all odd-coord inner cells as open
        room_cells = [(c, r) for r in range(1, H, 2) for c in range(1, W, 2)]
        in_maze = set()

        start = random.choice(room_cells)
        in_maze.add(start)
        g[start[1]][start[0]] = 1

        # frontier: list of (wall_cell, room_behind_wall)
        def add_frontiers(rc):
            c, r = rc
            for dc, dr in [(2,0),(-2,0),(0,2),(0,-2)]:
                nc, nr = c+dc, r+dr
                if 0 < nc < W and 0 < nr < H and (nc,nr) not in in_maze:
                    frontiers.append(((c+dc//2, r+dr//2), (nc, nr)))

        frontiers = []
        add_frontiers(start)

        while frontiers:
            random.shuffle(frontiers)
            wall, nxt = frontiers.pop()
            if nxt in in_maze:
                continue
            in_maze.add(nxt)
            g[nxt[1]][nxt[0]] = 1       # open the room
            g[wall[1]][wall[0]] = 1     # open the corridor between
            add_frontiers(nxt)

        # Add some extra loops so the slide graph is richer
        extra_opens = max(4, len(room_cells) // 3)
        candidates = [(c, r) for r in range(1, H-1) for c in range(1, W-1)
                       if g[r][c] == 0 and r % 2 == 0 and c % 2 == 0]
        random.shuffle(candidates)
        for c, r in candidates[:extra_opens]:
            g[r][c] = 1

        return g

    # ── Greedy BFS solver: collect all coins via slides ───────────────────────
    def solve(grid, start, adj):
        dps, _ = build_slide_graph(grid, start[0], start[1])
        # All passable cells (excluding start) get coins
        all_coins = set()
        for src, edges in adj.items():
            for dest, cells in edges:
                all_coins.update(cells)
        all_coins.discard(start)

        coins = set(all_coins)
        path = [start]
        cur = start

        while coins:
            # BFS over decision points to find nearest slide that crosses a coin
            queue = [(cur, [])]
            visited = {cur}
            found = None
            while queue:
                pos, steps = queue.pop(0)
                for dest, cells in adj.get(pos, []):
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
            # Trace the full path and erase coins
            for i in range(len(found) - 1):
                p1, p2 = found[i], found[i+1]
                for cell in slide_cells(p1[0], p1[1], p2[0], p2[1]):
                    coins.discard(cell)
                path.append(p2)
            cur = found[-1]

        return path, all_coins

    # ── Build one valid room ──────────────────────────────────────────────────
    def build_room():
        for _ in range(200):
            grid = carve_maze()
            # pick a random open inner cell as start
            open_inner = [(c, r) for r in range(1, ROWS-1)
                           for c in range(1, COLS-1) if grid[r][c] == 1]
            if not open_inner:
                continue
            sx, sy = random.choice(open_inner)
            dps, adj = build_slide_graph(grid, sx, sy)
            if len(dps) < 8:
                continue
            if not is_strongly_connected(adj, dps):
                continue
            # Verify all passable cells are actually reachable and collectable
            path, coins = solve(grid, (sx, sy), adj)
            if len(coins) >= 20:
                return grid, path, sx, sy, coins

        # Absolute fallback: open corridor grid
        grid = [[0]*COLS for _ in range(ROWS)]
        for r in range(1, ROWS-1):
            for c in range(1, COLS-1):
                grid[r][c] = 1
        dps, adj = build_slide_graph(grid, 4, 6)
        path, coins = solve(grid, (4, 6), adj)
        return grid, path, 4, 6, coins

    num_rooms = 4
    rooms = []
    for i in range(num_rooms):
        grid, path, start_x, start_y, coins = build_room()
        rooms.append({
            "grid": grid,
            "path": path,
            "start": (start_x, start_y),
            "coins": list(coins)
        })
        
    room_duration = 7.5
    total_duration = num_rooms * room_duration
    
    styles = []
    keyframe_animations = []
    
    for idx, r_data in enumerate(rooms):
        path = r_data["path"]
        grid = r_data["grid"]
        start_x, start_y = r_data["start"]
        
        v = 10.0
        pause = 0.12
        
        play_time = room_duration - 0.8
        raw_durations = []
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i+1]
            d = abs(x2 - x1) + abs(y2 - y1)
            raw_durations.append(d / v + pause)
            
        total_raw = sum(raw_durations) if raw_durations else 1.0
        scale_t = play_time / total_raw
        
        timeline = []
        cur_t = 0.4
        timeline.append({"time": cur_t, "x": start_x, "y": start_y, "scale": (1.0, 1.0)})
        
        dots_collected = {}
        
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i+1]
            dx = x2 - x1
            dy = y2 - y1
            d = abs(dx) + abs(dy)
            
            slide_dur = (d / v) * scale_t
            pause_dur = pause * scale_t
            
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
            timeline.append({"time": cur_t, "x": x2, "y": y2, "scale": (1.0, 1.0)})
            
            if dx != 0:
                sq_x, sq_y = 0.8, 1.2
                st_x, st_y = 1.1, 0.95
            else:
                sq_x, sq_y = 1.2, 0.8
                st_x, st_y = 0.95, 1.1
                
            timeline.append({"time": cur_t + 0.04 * scale_t, "x": x2, "y": y2, "scale": (sq_x, sq_y)})
            timeline.append({"time": cur_t + 0.08 * scale_t, "x": x2, "y": y2, "scale": (st_x, st_y)})
            
            cur_t += pause_dur
            timeline.append({"time": cur_t, "x": x2, "y": y2, "scale": (1.0, 1.0)})
            
        room_start_pct = (idx * room_duration / total_duration) * 100.0
        room_end_pct = ((idx + 1) * room_duration / total_duration) * 100.0
        
        player_kf = []
        for step in timeline:
            t_abs = idx * room_duration + step["time"]
            pct = (t_abs / total_duration) * 100.0
            px = step["x"] * TILE + TILE / 2
            py = step["y"] * TILE + TILE / 2
            sx, sy = step["scale"]
            player_kf.append(f"      {pct:.2f}% {{ transform: translate({px}px, {py}px) scale({sx}, {sy}); opacity: 1; }}")
            
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
            t_abs = idx * room_duration + t_c
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
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" width="240" height="380" viewBox="0 0 240 380">')
    svg.append('  <defs>')
    svg.append('    <linearGradient id="wallGrad" x1="0" y1="0" x2="1" y2="1">')
    svg.append('      <stop offset="0%" stop-color="#2d0b5a"/>')
    svg.append('      <stop offset="100%" stop-color="#0e021a"/>')
    svg.append('    </linearGradient>')
    svg.append('    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">')
    svg.append('      <feGaussianBlur stdDeviation="2" result="blur"/>')
    svg.append('      <feMerge>')
    svg.append('        <feMergeNode in="blur"/>')
    svg.append('        <feMergeNode in="SourceGraphic"/>')
    svg.append('      </feMerge>')
    svg.append('    </filter>')
    svg.append('    <clipPath id="gridClip">')
    svg.append('      <rect x="0" y="0" width="216" height="312"/>')
    svg.append('    </clipPath>')
    svg.append('  </defs>')
    
    svg.append('  <style>')
    svg.append('    @keyframes pulse {')
    svg.append('      0% { opacity: 0.6; }')
    svg.append('      50% { opacity: 1.0; }')
    svg.append('      100% { opacity: 0.6; }')
    svg.append('    }')
    svg.append('    .pulse-text { animation: pulse 2s infinite ease-in-out; }')
    svg.extend(styles)
    svg.extend(keyframe_animations)
    svg.append('  </style>')
    
    svg.append('  <rect width="240" height="380" fill="#08020d" rx="8" stroke="#7b2cbf" stroke-width="2"/>')
    svg.append('  <rect x="2" y="2" width="236" height="44" fill="#140526" rx="6"/>')
    svg.append('  <text x="120" y="24" text-anchor="middle" font-size="12" fill="#ffb703" font-family="monospace" font-weight="bold">🛡️ TOMB OF THE MASK</text>')
    svg.append('  <text x="120" y="38" text-anchor="middle" font-size="8" fill="#00f5d4" font-family="monospace" font-weight="bold" class="pulse-text">🤖 AUTOPLAY BOT</text>')
    
    svg.append('  <g transform="translate(12, 48)">')
    svg.append('    <rect width="216" height="312" fill="#0c0314" stroke="#7b2cbf" stroke-width="2" rx="4"/>')
    
    for idx, r_data in enumerate(rooms):
        grid = r_data["grid"]
        svg.append(f'    <g id="room-{idx}" clip-path="url(#gridClip)">')
        svg.append('      <g stroke="#1b0e36" stroke-width="0.5" stroke-dasharray="1,5">')
        for c in range(1, COLS):
            x = c * TILE
            svg.append(f'        <line x1="{x}" y1="0" x2="{x}" y2="312"/>')
        for r in range(1, ROWS):
            y = r * TILE
            svg.append(f'        <line x1="0" y1="{y}" x2="216" y2="{y}"/>')
        svg.append('      </g>')
        
        for r in range(ROWS):
            for c in range(COLS):
                val = grid[r][c]
                x = c * TILE
                y = r * TILE
                if val == 0:
                    svg.append(f'      <rect x="{x}" y="{y}" width="24" height="24" fill="url(#wallGrad)" stroke="#7b2cbf" stroke-width="0.5" rx="2"/>')
                    svg.append(f'      <rect x="{x+2}" y="{y+2}" width="20" height="20" fill="none" stroke="#210535" stroke-width="0.5"/>')
                elif val == 1:
                    if (c, r) in r_data["coins"]:
                        svg.append(f'      <circle id="dot-{idx}-{c}-{r}" cx="{x+12}" cy="{y+12}" r="3" fill="#ffb703"/>')
                        
        svg.append(f'      <g id="player-{idx}" filter="url(#glow)">')
        svg.append('        <rect x="-10" y="-10" width="20" height="20" rx="4" fill="#ffb703"/>')
        svg.append('        <path d="M-10,-10 L-14,-14 L-6,-10 Z" fill="#ffb703"/>')
        svg.append('        <path d="M10,-10 L14,-14 L6,-10 Z" fill="#ffb703"/>')
        svg.append('        <rect x="-6" y="-4" width="4" height="6" fill="#08020d"/>')
        svg.append('        <rect x="2" y="-4" width="4" height="6" fill="#08020d"/>')
        svg.append('        <rect x="-5" y="-2" width="2" height="2" fill="#ffffff"/>')
        svg.append('        <rect x="3" y="-2" width="2" height="2" fill="#ffffff"/>')
        svg.append('      </g>')
        svg.append('    </g>')
        
    svg.append('  </g>')
    
    svg.append('  <rect x="12" y="48" width="216" height="312" fill="none" stroke="#7b2cbf" stroke-width="2" rx="4"/>')
    svg.append('  <text x="120" y="372" text-anchor="middle" font-size="7" fill="#64748b" font-family="monospace">⚡ PROCEDURAL LEVEL SOLVER</text>')
    svg.append('</svg>')
    
    return "\n".join(svg)

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
    with open(f"{output}/skyline_v3.svg", "w", encoding="utf-8") as f:
        f.write(generate_svg(today.year, today.month, all_data.get(cur, {})))
        
    with open(f"{output}/tomb_v1.svg", "w", encoding="utf-8") as f:
        f.write(generate_tomb_svg())
        
    with open(f"{output}/index.html", "w", encoding="utf-8") as f:
        f.write(generate_html(all_data))
        
    print("Concluído!")

if __name__ == "__main__":
    main()
