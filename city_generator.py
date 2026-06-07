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
    return 210

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
    
    for d in range(1, last_day + 1):
        x = ML + (d - 1) * (LOT_W + GAP)
        commits = counts.get(d, 0)
        cur = datetime.date(year, month, d)
        
        is_today = cur == today
        is_future = cur > today
        day_seed = (year * 100 + month) * 100 + d
        
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
            o.append(f'<rect x="{x + LOT_W//2 - 7}" y="{GROUND_Y - h - 16}" width="14" height="10" fill="#f59e0b" rx="2"/>')
            o.append(f'<text x="{x + LOT_W//2}" y="{GROUND_Y - h - 8}" text-anchor="middle" font-size="8" fill="#0f172a" font-weight="bold" font-family="{FONT}">{commits}</text>')
        
        # Etiquetas dos Dias
        lbl_color = "#f59e0b" if is_today else "#94a3b8"
        font_w = "bold" if is_today else "normal"
        o.append(f'<text x="{x + LOT_W//2}" y="{GROUND_Y + 20}" text-anchor="middle" font-size="10" fill="{lbl_color}" font-weight="{font_w}" font-family="{FONT}">{d}</text>')
        
        if is_today:
            # Apontador de destaque para o dia de hoje
            o.append(f'<polygon points="{x+LOT_W//2-4},{GROUND_Y+25} {x+LOT_W//2+4},{GROUND_Y+25} {x+LOT_W//2},{GROUND_Y+30}" fill="#f59e0b"/>')

    draw_street(o, svg_w)
    
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
    
    for (let d = 1; d <= lastDay; d++) {{
        const x = ML + (d - 1) * (LOT_W + GAP);
        const commits = counts[d] || 0;
        const curDate = new Date(yr, mo - 1, d);
        const tdToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        const isToday = curDate.getTime() === tdToday.getTime();
        const isFuture = curDate > tdToday;
        const daySeed = (yr * 100 + mo) * 100 + d;
        
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
            let h = commits <= 3 ? 60 : commits <= 6 ? 110 : commits <= 10 ? 160 : 210;
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
            
            // Emblema de commits
            svg += `<rect x="${{x+LOT_W/2-7}}" y="${{yPos-16}}" width="14" height="10" fill="#f59e0b" rx="2"/>`;
            svg += `<text x="${{x+LOT_W/2}}" y="${{yPos-8}}" text-anchor="middle" font-size="8" fill="#0f172a" font-weight="bold" font-family="monospace">${{commits}}</text>`;
        }}
        
        // Etiqueta do Dia
        let lblColor = isToday ? "#f59e0b" : "#94a3b8";
        let fontW = isToday ? "bold" : "normal";
        svg += `<text x="${{x + LOT_W/2}}" y="${{GROUND_Y+20}}" text-anchor="middle" font-size="10" fill="${{lblColor}}" font-weight="${{fontW}}" font-family="monospace">${{d}}</text>`;
        
        if (isToday) {{
            svg += `<polygon points="${{x+LOT_W/2-4}},${{GROUND_Y+25}} ${{x+LOT_W/2+4}},${{GROUND_Y+25}} ${{x+LOT_W/2}},${{GROUND_Y+30}}" fill="#f59e0b"/>`;
        }}
    }}
    
    // Calçada e Rua
    svg += `<rect x="0" y="${{GROUND_Y}}" width="${{svgW}}" height="8" fill="#475569"/>`;
    svg += `<rect x="0" y="${{GROUND_Y+8}}" width="${{svgW}}" height="28" fill="#1e293b"/>`;
    svg += `<line x1="0" y1="${{GROUND_Y+22}}" x2="${{svgW}}" y2="${{GROUND_Y+22}}" stroke="#e2e8f0" stroke-width="2" stroke-dasharray="12,12"/>`;
    
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
        
    print("Concluído!")

if __name__ == "__main__":
    main()
