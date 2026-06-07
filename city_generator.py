import os
import json
import random
import datetime
import urllib.request
import urllib.error

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER  = os.environ.get("GITHUB_USER", "EvaniIdo")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

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
        chunk = gh_get(f"https://api.github.com/user/repos?per_page=100&page={page}&affiliation=owner")
        if not chunk:
            break
        repos += [r["full_name"] for r in chunk]
        if len(chunk) < 100:
            break
        page += 1
    return repos

def commits_by_day(year, month):
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    since = f"{year}-{month:02d}-01T00:00:00Z"
    until = f"{year}-{month:02d}-{last_day}T23:59:59Z"
    counts = {d: 0 for d in range(1, last_day + 1)}
    for repo in fetch_repos():
        url = (f"https://api.github.com/repos/{repo}/commits"
               f"?author={GITHUB_USER}&since={since}&until={until}&per_page=100")
        items = gh_get(url)
        if not isinstance(items, list):
            continue
        for item in items:
            try:
                d = int(item["commit"]["author"]["date"][8:10])
                if d in counts:
                    counts[d] += 1
            except (KeyError, ValueError):
                pass
    return counts

# ── SVG generation ─────────────────────────────────────────────────────────────

W, GROUND_Y, H = 820, 295, 380
LOT_W, GAP, ML = 24, 2, 20
FONT = "monospace"
PALETTES = ["#4f46e5","#7c3aed","#2563eb","#0891b2","#0d9488","#1d4ed8","#6d28d9","#7e22ce"]
WIN_COLORS = ["#fef08a","#fde68a","#fed7aa","#ffffff"]

def bh(commits):
    if commits == 0: return 0
    if commits == 1: return 28
    if commits <= 3: return 52
    if commits <= 6: return 90
    if commits <= 10: return 140
    return 200

def generate_svg(year, month, counts):
    import calendar
    today    = datetime.date.today()
    last_day = calendar.monthrange(year, month)[1]
    mname    = datetime.date(year, month, 1).strftime("%B %Y")
    svg_w    = max(W, ML*2 + last_day*(LOT_W+GAP))
    o = []

    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{H}" viewBox="0 0 {svg_w} {H}">')
    o.append(f'<defs>'
             f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0%" stop-color="#0a0a1a"/><stop offset="100%" stop-color="#1a1a3e"/>'
             f'</linearGradient></defs>')
    o.append(f'<rect width="{svg_w}" height="{H}" fill="url(#sky)"/>')

    # stars
    rng = random.Random(7)
    for _ in range(80):
        sx,sy = rng.randint(0,svg_w), rng.randint(0,GROUND_Y-30)
        op,r  = round(rng.uniform(0.3,1.0),2), round(rng.uniform(0.5,1.5),1)
        o.append(f'<circle cx="{sx}" cy="{sy}" r="{r}" fill="white" opacity="{op}"/>')

    # ground
    o.append(f'<rect x="0" y="{GROUND_Y}" width="{svg_w}" height="{H-GROUND_Y}" fill="#111827"/>')
    o.append(f'<rect x="0" y="{GROUND_Y}" width="{svg_w}" height="3" fill="#374151"/>')

    # title
    o.append(f'<text x="{svg_w//2}" y="22" text-anchor="middle" font-size="12" '
             f'fill="#e5e7eb" font-family="{FONT}" font-weight="bold">&#x1F4C5; {mname}</text>')

    for d in range(1, last_day+1):
        x       = ML + (d-1)*(LOT_W+GAP)
        commits = counts.get(d, 0)
        cur     = datetime.date(year, month, d)
        is_today   = cur == today
        is_future  = cur > today
        seed    = (year*100+month)*100+d
        pal     = PALETTES[seed % len(PALETTES)]
        h_b     = bh(commits)
        by_     = GROUND_Y - h_b

        if is_future:
            o.append(f'<rect x="{x}" y="{GROUND_Y-40}" width="{LOT_W}" height="43" '
                     f'fill="none" stroke="#374151" stroke-width="1" stroke-dasharray="3,3" rx="2"/>')
            mx = x + LOT_W//2
            o.append(f'<line x1="{mx}" y1="{GROUND_Y-40}" x2="{mx}" y2="{GROUND_Y-55}" stroke="#6b7280" stroke-width="1"/>')
            o.append(f'<line x1="{mx}" y1="{GROUND_Y-55}" x2="{mx+8}" y2="{GROUND_Y-55}" stroke="#6b7280" stroke-width="1"/>')
        elif commits == 0:
            o.append(f'<rect x="{x}" y="{GROUND_Y+3}" width="{LOT_W}" height="60" fill="#111827" rx="1"/>')
            for i in range(3):
                o.append(f'<rect x="{x+LOT_W//2-1}" y="{GROUND_Y+10+i*16}" width="2" height="8" fill="#374151"/>')
        elif commits == 1:
            o.append(f'<rect x="{x}" y="{GROUND_Y-18}" width="{LOT_W}" height="21" fill="#166534" rx="2"/>')
            tx = x + LOT_W//2
            o.append(f'<rect x="{tx-1}" y="{GROUND_Y-13}" width="2" height="8" fill="#854d0e"/>')
            o.append(f'<circle cx="{tx}" cy="{GROUND_Y-18}" r="5" fill="#15803d"/>')
        else:
            o.append(f'<rect x="{x}" y="{by_}" width="{LOT_W}" height="{h_b}" fill="{pal}" rx="2"/>')
            o.append(f'<rect x="{x}" y="{by_}" width="{LOT_W}" height="4" fill="white" opacity="0.15" rx="2"/>')
            # windows
            wrng = random.Random(seed+99)
            ww,wh = 3,3
            cols_w = max(1,(LOT_W-4)//(ww+3))
            rows_w = max(1,(h_b-8)//(wh+4))
            for row in range(rows_w):
                for col_i in range(cols_w):
                    if wrng.random() < 0.65:
                        wx = x+3+col_i*(ww+3)
                        wy = by_+6+row*(wh+4)
                        wc = WIN_COLORS[wrng.randint(0,len(WIN_COLORS)-1)]
                        o.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="{wc}" opacity="0.9"/>')
            # antenna on skyscrapers
            if h_b >= 140:
                ax = x+LOT_W//2
                o.append(f'<line x1="{ax}" y1="{by_}" x2="{ax}" y2="{by_-12}" stroke="#9ca3af" stroke-width="1"/>')
                o.append(f'<circle cx="{ax}" cy="{by_-13}" r="2" fill="#ef4444" opacity="0.8"/>')
            # commit count
            badge_y = max(by_-4, 10)
            o.append(f'<text x="{x+LOT_W//2}" y="{badge_y}" text-anchor="middle" '
                     f'font-size="6" fill="#fbbf24" font-family="{FONT}">{commits}</text>')

        # day label
        col = "#f59e0b" if is_today else "#6b7280"
        o.append(f'<text x="{x+LOT_W//2}" y="{GROUND_Y+18}" text-anchor="middle" '
                 f'font-size="6" fill="{col}" font-family="{FONT}">{d}</text>')

        if is_today:
            lx = x+LOT_W//2
            o.append(f'<line x1="{lx}" y1="{GROUND_Y+22}" x2="{lx}" y2="{H-5}" '
                     f'stroke="#f59e0b" stroke-width="1" stroke-dasharray="2,2"/>')

    # legend
    ly = H-22
    items = [("#111827","0 commits"),("#166534","1 commit"),
             ("#4f46e5","2-6"),("#7c3aed","7-10"),("#0891b2","11+")]
    lx = ML
    for color, label in items:
        o.append(f'<rect x="{lx}" y="{ly}" width="8" height="8" fill="{color}" rx="1"/>')
        o.append(f'<text x="{lx+10}" y="{ly+7}" font-size="7" fill="#9ca3af" font-family="{FONT}">{label}</text>')
        lx += 110

    o.append("</svg>")
    return "\n".join(o)

def generate_html(all_data):
    data_json = json.dumps(all_data)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>GitHub City — EvaniIdo</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0a0a1a;color:#e5e7eb;font-family:monospace;min-height:100vh;
     display:flex;flex-direction:column;align-items:center;padding:24px}}
h1{{font-size:1.4rem;color:#f59e0b;margin-bottom:18px;letter-spacing:2px;text-align:center}}
.controls{{display:flex;gap:12px;align-items:center;margin-bottom:20px}}
label{{color:#9ca3af;font-size:.9rem}}
select{{background:#1f2937;color:#e5e7eb;border:1px solid #374151;border-radius:6px;
        padding:6px 14px;font-family:monospace;font-size:.9rem;cursor:pointer}}
select:focus{{outline:none;border-color:#f59e0b}}
canvas{{border-radius:12px;border:1px solid #1f2937;max-width:100%}}
.legend{{display:flex;gap:18px;margin-top:14px;flex-wrap:wrap;justify-content:center}}
.leg{{display:flex;align-items:center;gap:6px;font-size:.75rem;color:#9ca3af}}
.swatch{{width:12px;height:12px;border-radius:2px;flex-shrink:0}}
</style>
</head>
<body>
<h1>&#x1F3D9;&#xFE0F; GitHub City</h1>
<div class="controls">
  <label for="sel">Mês:</label>
  <select id="sel"></select>
</div>
<canvas id="c"></canvas>
<div class="legend">
  <div class="leg"><div class="swatch" style="background:#111827"></div>Nenhum commit</div>
  <div class="leg"><div class="swatch" style="background:#166534"></div>1 commit (pra&ccedil;a)</div>
  <div class="leg"><div class="swatch" style="background:#4f46e5"></div>2&ndash;3 commits</div>
  <div class="leg"><div class="swatch" style="background:#7c3aed"></div>4&ndash;6 commits</div>
  <div class="leg"><div class="swatch" style="background:#0891b2"></div>7&ndash;10 commits</div>
  <div class="leg"><div class="swatch" style="background:#0d9488"></div>11+ commits</div>
  <div class="leg"><div class="swatch" style="background:transparent;border:1px dashed #6b7280"></div>Futuro</div>
</div>
<script>
const DATA={data_json};
const PAL=["#4f46e5","#7c3aed","#2563eb","#0891b2","#0d9488","#1d4ed8","#6d28d9","#7e22ce"];
const WIN=["#fef08a","#fde68a","#fed7aa","#ffffff"];
function rng(s){{let v=s;return()=>{{v=(v*9301+49297)%233280;return v/233280;}}}}
function bh(c){{if(!c)return 0;if(c===1)return 28;if(c<=3)return 52;if(c<=6)return 90;if(c<=10)return 140;return 200;}}
function draw(yr,mo,counts){{
  const today=new Date(),dim=new Date(yr,mo,0).getDate();
  const LOT=26,GAP=2,ML=20,GY=295,H=380,W=Math.max(820,ML*2+dim*(LOT+GAP));
  const cv=document.getElementById("c"),ctx=cv.getContext("2d");
  cv.width=W;cv.height=H;
  const sg=ctx.createLinearGradient(0,0,0,H);
  sg.addColorStop(0,"#0a0a1a");sg.addColorStop(1,"#1a1a3e");
  ctx.fillStyle=sg;ctx.fillRect(0,0,W,H);
  const sr=rng(7);
  for(let i=0;i<80;i++){{
    const sx=sr()*W,sy=sr()*GY,op=.3+sr()*.7,r=.5+sr()*1.5;
    ctx.globalAlpha=op;ctx.fillStyle="#fff";
    ctx.beginPath();ctx.arc(sx,sy,r,0,Math.PI*2);ctx.fill();
  }}
  ctx.globalAlpha=1;
  ctx.fillStyle="#111827";ctx.fillRect(0,GY,W,H-GY);
  ctx.fillStyle="#374151";ctx.fillRect(0,GY,W,3);
  const mn=["Janeiro","Fevereiro","Mar\u00e7o","Abril","Maio","Junho",
             "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
  ctx.fillStyle="#e5e7eb";ctx.font="bold 13px monospace";ctx.textAlign="center";
  ctx.fillText("\uD83D\uDCC5 "+mn[mo-1]+" "+yr,W/2,22);
  for(let d=1;d<=dim;d++){{
    const x=ML+(d-1)*(LOT+GAP),c=counts[d]||0;
    const td=new Date(yr,mo-1,d),tt=new Date(today.getFullYear(),today.getMonth(),today.getDate());
    const isToday=td.getTime()===tt.getTime(),isFut=td>tt;
    const seed=(yr*100+mo)*100+d,pal=PAL[seed%PAL.length];
    const h=bh(c),by=GY-h,r2=rng(seed+99);
    if(isFut){{
      ctx.strokeStyle="#374151";ctx.lineWidth=1;ctx.setLineDash([3,3]);
      ctx.strokeRect(x,GY-40,LOT,43);ctx.setLineDash([]);
      const mx=x+LOT/2;
      ctx.strokeStyle="#6b7280";ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(mx,GY-40);ctx.lineTo(mx,GY-55);ctx.stroke();
      ctx.beginPath();ctx.moveTo(mx,GY-55);ctx.lineTo(mx+8,GY-55);ctx.stroke();
    }}else if(!c){{
      ctx.fillStyle="#111827";ctx.fillRect(x,GY+3,LOT,60);
      ctx.fillStyle="#374151";
      for(let i=0;i<3;i++)ctx.fillRect(x+LOT/2-1,GY+10+i*16,2,8);
    }}else if(c===1){{
      ctx.fillStyle="#166534";ctx.fillRect(x,GY-18,LOT,21);
      ctx.fillStyle="#854d0e";ctx.fillRect(x+LOT/2-1,GY-13,2,8);
      ctx.fillStyle="#15803d";ctx.beginPath();ctx.arc(x+LOT/2,GY-18,5,0,Math.PI*2);ctx.fill();
    }}else{{
      ctx.fillStyle=pal;ctx.beginPath();ctx.roundRect(x,by,LOT,h,2);ctx.fill();
      ctx.fillStyle="rgba(255,255,255,.12)";ctx.fillRect(x,by,LOT,4);
      const ww=3,wh=3,cw=Math.max(1,Math.floor((LOT-4)/(ww+3))),rw=Math.max(1,Math.floor((h-8)/(wh+4)));
      for(let row=0;row<rw;row++){{
        for(let col=0;col<cw;col++){{
          if(r2()<.65){{
            ctx.globalAlpha=.9;ctx.fillStyle=WIN[Math.floor(r2()*WIN.length)];
            ctx.fillRect(x+3+col*(ww+3),by+6+row*(wh+4),ww,wh);ctx.globalAlpha=1;
          }}
        }}
      }}
      if(h>=140){{
        const ax=x+LOT/2;
        ctx.strokeStyle="#9ca3af";ctx.lineWidth=1;
        ctx.beginPath();ctx.moveTo(ax,by);ctx.lineTo(ax,by-12);ctx.stroke();
        ctx.fillStyle="#ef4444";ctx.globalAlpha=.8;
        ctx.beginPath();ctx.arc(ax,by-13,2,0,Math.PI*2);ctx.fill();ctx.globalAlpha=1;
      }}
      ctx.fillStyle="#fbbf24";ctx.font="6px monospace";ctx.textAlign="center";
      ctx.fillText(c,x+LOT/2,Math.max(by-4,10));
    }}
    ctx.fillStyle=isToday?"#f59e0b":"#6b7280";
    ctx.font="6px monospace";ctx.textAlign="center";
    ctx.fillText(d,x+LOT/2,GY+18);
    if(isToday){{
      const lx=x+LOT/2;ctx.strokeStyle="#f59e0b";ctx.lineWidth=1;ctx.setLineDash([2,2]);
      ctx.beginPath();ctx.moveTo(lx,GY+22);ctx.lineTo(lx,H-5);ctx.stroke();ctx.setLineDash([]);
    }}
  }}
}}
const sel=document.getElementById("sel");
Object.keys(DATA).sort().reverse().forEach(k=>{{
  const o=document.createElement("option");o.value=k;o.textContent=k;sel.appendChild(o);
}});
sel.addEventListener("change",()=>{{const[y,m]=sel.value.split("-").map(Number);draw(y,m,DATA[sel.value]||{{}});}});
const[iy,im]=sel.value.split("-").map(Number);draw(iy,im,DATA[sel.value]||{{}});
</script>
</body>
</html>
"""

def main():
    today  = datetime.date.today()
    output = "dist"
    os.makedirs(output, exist_ok=True)
    all_data = {}
    for i in range(6):
        m, y = today.month - i, today.year
        while m < 1: m += 12; y -= 1
        key = f"{y}-{m:02d}"
        counts = commits_by_day(y, m)
        all_data[key] = counts
        print(f"  {key}: {sum(counts.values())} commits")
    with open(f"{output}/data.json","w") as f:
        json.dump(all_data, f)
    cur = f"{today.year}-{today.month:02d}"
    with open(f"{output}/city.svg","w",encoding="utf-8") as f:
        f.write(generate_svg(today.year, today.month, all_data.get(cur,{})))
    with open(f"{output}/index.html","w",encoding="utf-8") as f:
        f.write(generate_html(all_data))
    print("Done — dist/city.svg + dist/index.html")

if __name__ == "__main__":
    main()
