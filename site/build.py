#!/usr/bin/env python3
"""site/build.py - builds the /sunpoint page and the article from one set of texts (site/strings.py).

Output:
  site/dist/<host>/sunpoint/index.html (+ assets/)   one file, three languages (EN / KK / RU) with a switcher
  docs/ARTICLE.en.md, docs/ARTICLE.kk.md, docs/ARTICLE.ru.md

Usage:  python3 -I site/build.py
The page has no external requests: fonts are served from ./assets, no trackers, no cookies.
"""
import os, sys, html, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from strings import T, LANGS, tr, REPO, REVIEW   # noqa: E402

SITES = [("sun-agi.com", "en"), ("galymzhan.kz", "ru")]      # host, default language
LANG_NAME = {"en": "ENG", "kk": "ҚАЗ", "ru": "РУС"}


def esc(s):
    return html.escape(s, quote=False)


def t(key):
    """One text in three languages; CSS shows the active one."""
    return "".join(f'<span data-l="{l}" lang="{l}">{esc(tr(key, l))}</span>' for l in LANGS)


def num(en, loc):
    """A number: dot for English, comma for Kazakh and Russian."""
    return f'<span data-l="en">{en}</span><span data-l="kk">{loc}</span><span data-l="ru">{loc}</span>'


# ---------------------------------------------------------------- the moment strip (SVG)
def strip_svg():
    X = lambda s: 180 + 15.6 * s          # seconds -10..+10 -> x
    Y = lambda v: 150 - 2.6 * v           # per cent 0..45 -> y
    pts = [(-10, 9.7), (-9, 10.5), (-8, 9.9), (-7, 10.9), (-6, 9.4), (-5, 10.2), (-4, 10.7), (-3, 9.8),
           (-2, 10.3), (-1, 10.0), (-0.12, 10.4), (0, 41.9), (1, 38.6), (2, 35.9), (3, 33.7), (4, 31.9),
           (5, 30.5), (6, 29.4), (7, 28.6), (8, 28.0), (9, 27.5), (10, 27.2)]
    d = "M" + " L".join(f"{X(a):.1f} {Y(b):.1f}" for a, b in pts)
    ticks = "".join(f'<line x1="{X(s):.1f}" y1="150" x2="{X(s):.1f}" y2="{155 if s % 5 else 158}" class="tk"/>' for s in range(-10, 11))
    def lab(key, x, y, anchor="start", cls="lb"):
        return "".join(f'<text data-l="{l}" x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}">{esc(tr(key, l))}</text>' for l in LANGS)
    return f'''<svg class="strip" viewBox="0 0 360 200" role="img" aria-labelledby="stripcap">
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <linearGradient id="after" x1="0" x2="1"><stop offset="0" stop-color="#bfe6ff" stop-opacity=".20"/><stop offset="1" stop-color="#bfe6ff" stop-opacity=".04"/></linearGradient>
  </defs>
  <rect x="{X(0):.1f}" y="24" width="{X(10) - X(0):.1f}" height="126" fill="url(#after)"/>
  <line x1="{X(-10):.1f}" y1="{Y(10.05):.1f}" x2="{X(10):.1f}" y2="{Y(10.05):.1f}" class="exp"/>
  <line x1="{X(-10):.1f}" y1="150" x2="{X(10):.1f}" y2="150" class="ax"/>{ticks}
  <line x1="{X(0):.1f}" y1="24" x2="{X(0):.1f}" y2="150" class="alertline"/>
  <path d="{d}" class="trace" pathLength="1"/>
  <circle cx="{X(0):.1f}" cy="{Y(41.9):.1f}" r="5.5" class="flash" filter="url(#glow)"/>
  <rect x="{X(10) - 4:.1f}" y="{Y(26.29) - 4:.1f}" width="8" height="8" transform="rotate(45 {X(10):.1f} {Y(26.29):.1f})" class="pred"/>
  <circle cx="{X(10):.1f}" cy="{Y(27.2):.1f}" r="3" class="real"/>
  {lab("fig_exp", X(-10), Y(10.05) - 7)}
  {lab("fig_alert", X(0) - 8, Y(41.9) + 2, "end", "lb strong")}
  {lab("fig_reflex", X(0) - 8, Y(41.9) + 16, "end")}
  {lab("fig_pred", X(10), Y(26.29) - 12, "end")}
  {lab("fig_real", X(10), Y(27.2) + 19, "end", "lb strong")}
  <text x="{X(-10):.1f}" y="170" class="tl">−10</text><text x="{X(0):.1f}" y="170" text-anchor="middle" class="tl">0</text><text x="{X(10):.1f}" y="170" text-anchor="end" class="tl">+10</text>
  {lab("fig_before", X(-5), 190, "middle", "zone")}
  {lab("fig_after", X(5), 190, "middle", "zone")}
</svg>'''


# ---------------------------------------------------------------- page
CSS = r'''
@font-face{font-family:"Bitter";src:url(assets/bitter.woff2) format("woff2");font-weight:300 900;font-display:swap}
@font-face{font-family:"Source Sans 3";src:url(assets/sourcesans3.woff2) format("woff2");font-weight:300 800;font-display:swap}
:root{--paper:#fff;--cloud:#eef4f9;--ink:#0a1f3c;--ink2:#465a75;--deep:#1246a8;--sky:#5ab4ff;--arc:#bfe6ff;--hot:#f2fbff;
  --teal:#177e8c;--turq:#37b6c1;--sun:#a8730a;--no:#bf4333;--line:#d3dfea;
  --serif:"Bitter",Georgia,"Times New Roman",serif;--sans:"Source Sans 3",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,"Cascadia Mono",Consolas,"DejaVu Sans Mono","Liberation Mono",monospace}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font:400 1.0625rem/1.6 var(--sans)}
html[data-lang="en"] [data-l]:not([data-l="en"]),html[data-lang="kk"] [data-l]:not([data-l="kk"]),html[data-lang="ru"] [data-l]:not([data-l="ru"]){display:none!important}
a{color:var(--deep);text-underline-offset:.18em}
a:focus-visible,button:focus-visible{outline:3px solid var(--sky);outline-offset:3px;border-radius:4px}
.wrap{max-width:46rem;margin:0 auto;padding:0 1.25rem}

/* sky: the one loud place on the page */
.sky{position:relative;color:var(--hot);overflow:hidden;
  background:radial-gradient(95% 75% at 100% 0%,rgba(55,182,193,.62) 0%,rgba(55,182,193,0) 60%),linear-gradient(180deg,#071a36 0%,#0c2c66 58%,#1246a8 100%)}
.top{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding-top:1.1rem}
.mark{display:flex;align-items:center;gap:.55rem;font:700 1.15rem/1 var(--serif);letter-spacing:.01em;color:var(--hot);text-decoration:none}
.mark i{width:.8rem;height:.8rem;border-radius:50%;background:var(--hot);box-shadow:0 0 0 .22rem rgba(191,230,255,.28),0 0 1.1rem .15rem rgba(191,230,255,.75)}
.lang{display:flex;gap:.3rem}
.lang button{font:600 .82rem/1 var(--sans);letter-spacing:.04em;color:var(--hot);background:transparent;border:1px solid rgba(242,251,255,.38);border-radius:999px;padding:.5rem .7rem;cursor:pointer}
.lang button[aria-pressed="true"]{background:var(--hot);color:#0a1f3c;border-color:var(--hot)}
h1{font:800 clamp(2.35rem,9.2vw,4.5rem)/1.04 var(--serif);letter-spacing:-.012em;margin:2.6rem 0 1.1rem;text-wrap:balance}
.sub{font:400 clamp(1.12rem,3.6vw,1.4rem)/1.42 var(--serif);max-width:33em;margin:0 0 1.3rem;color:#e3f3ff}
.where{margin:0;font-size:.98rem;color:#cfe6fa}
.byline{margin:.25rem 0 0;font-size:.92rem;color:#a9c9e6;max-width:38em}
.cta{display:flex;flex-wrap:wrap;gap:.7rem;margin:1.5rem 0 0}
.cta a{display:inline-block;font:600 1rem/1.2 var(--sans);text-decoration:none;border-radius:.6rem;padding:.8rem 1.1rem}
.cta .a1{background:var(--hot);color:#0a1f3c}
.cta .a2{color:var(--hot);border:1px solid rgba(242,251,255,.5)}
figure{margin:0}
.moment{margin:2.2rem 0 0;max-width:36rem}
.strip{display:block;width:100%;height:auto;overflow:visible}
.strip .trace{fill:none;stroke:var(--hot);stroke-width:2;stroke-linejoin:round;stroke-linecap:round;stroke-dasharray:1;stroke-dashoffset:0;animation:draw 1.9s cubic-bezier(.6,0,.2,1) both}
.strip .exp{stroke:var(--sky);stroke-width:1;stroke-dasharray:3 4}
.strip .ax,.strip .tk{stroke:rgba(242,251,255,.55);stroke-width:1}
.strip .alertline{stroke:var(--arc);stroke-width:1;stroke-dasharray:1 3}
.strip .flash{fill:var(--hot);transform-box:fill-box;transform-origin:center;animation:flash 1.9s ease-out both}
.strip .pred{fill:none;stroke:var(--arc);stroke-width:1.4}
.strip .real{fill:var(--hot)}
.strip text{font-family:var(--sans);fill:#d7ecfd;font-size:10.5px}
.strip .strong{fill:var(--hot);font-weight:700;font-size:11.5px}
.strip .tl{fill:#a9c9e6;font-size:9.5px}
.strip .zone{fill:var(--hot);font-family:var(--serif);font-weight:600;font-size:11.5px}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
@keyframes flash{0%,46%{opacity:0;transform:scale(.2)}56%{opacity:1;transform:scale(2.6)}100%{opacity:1;transform:scale(1)}}
figcaption{font-size:.9rem;color:#a9c9e6;margin:.5rem 0 0;max-width:34em}
.clouds{display:block;width:100%;height:clamp(2.6rem,8vw,5rem);margin-top:2rem}

/* body: quiet documentation */
main{padding-bottom:3rem}
.lede{font:400 1.22rem/1.55 var(--serif);margin:1.6rem 0 0;max-width:36em}
h2{font:700 clamp(1.5rem,5vw,2rem)/1.18 var(--serif);margin:3.3rem 0 1rem;text-wrap:balance}
h3{font:700 1.08rem/1.3 var(--sans);margin:1.6rem 0 .3rem}
p{margin:0 0 1rem;max-width:38em}
ul,ol{margin:0 0 1rem;padding-left:1.25rem;max-width:38em}
li{margin:.4rem 0}
li b{font-weight:650}

.ledger{margin:0;border-top:2px solid var(--ink)}
.ledger>div{display:grid;grid-template-columns:1fr;gap:.1rem;padding:1rem 0 1.05rem;border-bottom:1px solid var(--line)}
.ledger dt{font:600 .98rem/1.3 var(--sans);color:var(--ink2)}
.ledger .v{margin:0;font:800 clamp(1.7rem,6.5vw,2.25rem)/1.1 var(--serif)}
.ledger .w{margin:.3rem 0 0;max-width:34em}
.ok .v,.ok .r{color:var(--teal)} .half .v,.half .r{color:var(--sun)} .no .v,.no .r{color:var(--no)} .na .v,.na .r{color:var(--ink2)}
@media (min-width:44rem){.ledger>div{grid-template-columns:11.5rem 1fr;column-gap:1.5rem}.ledger dt{grid-row:1/3;padding-top:.55rem}.ledger .w{grid-column:2}}

.formula{font:600 clamp(1.12rem,4vw,1.35rem)/1.4 var(--serif);margin:0 0 1.2rem;padding:1rem 1.1rem;background:var(--cloud);border-left:.3rem solid var(--deep);border-radius:0 .5rem .5rem 0;max-width:36em}
.say{margin:0 0 1.2rem;padding:0 0 0 1.1rem;border-left:.2rem solid var(--turq);max-width:36em}
.say p{font:400 1.14rem/1.55 var(--serif);margin:0 0 .5rem}
.say cite{font:600 .92rem/1.3 var(--sans);font-style:normal;color:var(--ink2)}
.heirs{list-style:none;padding:0;margin:0 0 1rem;display:grid;gap:.9rem;max-width:none}
.heirs li{margin:0;padding:.95rem 1.05rem 1rem;background:var(--cloud);border-radius:.6rem}
.heirs b{display:block;font:700 1.18rem/1.2 var(--serif);margin-bottom:.25rem}
@media (min-width:44rem){.heirs{grid-template-columns:repeat(3,1fr)}}
.machine{margin:0 0 1.2rem;padding:.85rem 1rem;background:#071a36;color:#e3f3ff;border-radius:.6rem;font:400 .93rem/1.55 var(--mono);overflow-wrap:anywhere;max-width:38em}

.chk{border-top:2px solid var(--ink);margin:0 0 1.5rem}
.chk>div{padding:.9rem 0 1rem;border-bottom:1px solid var(--line);display:grid;gap:.15rem}
.chk .c{font:700 1.1rem/1.3 var(--sans)}
.chk .m{color:var(--ink);max-width:36em}
.chk .r{font:800 1.08rem/1.25 var(--serif)}
@media (min-width:44rem){.chk>div{grid-template-columns:13rem 1fr 9.5rem;column-gap:1.4rem;align-items:start}.chk .r{text-align:right}}

.bars{margin:1.8rem 0 0;max-width:36rem}
.bars h3{margin:0 0 .6rem}
.bars .row{display:grid;grid-template-columns:1fr auto;column-gap:.8rem;align-items:baseline;margin:.55rem 0 0}
.bars .lab{font-size:.98rem}
.bars .val{font:700 1.05rem/1 var(--serif);font-variant-numeric:tabular-nums}
.bars .bar{grid-column:1/-1;height:.62rem;border-radius:.31rem;background:var(--cloud);overflow:hidden;margin-top:.25rem}
.bars .bar i{display:block;height:100%;border-radius:.31rem;background:linear-gradient(90deg,var(--deep),var(--sky))}
.bars .bar i.t{background:linear-gradient(90deg,var(--teal),var(--turq))}
.bars .bar i.g{background:#9db0c4}
.bars .note{font-size:.93rem;color:var(--ink2);margin:.7rem 0 0}
.pair{display:grid;gap:0 1.6rem}
@media (min-width:44rem){.pair{grid-template-columns:1fr 1fr}}
.word{margin:0;padding:1.3rem 1.25rem 1.4rem;background:linear-gradient(180deg,#071a36,#0c2c66);color:var(--hot);border-radius:.8rem}
.word p{font:400 clamp(1.1rem,3.6vw,1.26rem)/1.55 var(--serif);margin:0;max-width:none}
pre{margin:0 0 1rem;padding:1rem;background:#071a36;color:#e3f3ff;border-radius:.6rem;white-space:pre-wrap;overflow-wrap:anywhere;font:400 .9rem/1.55 var(--mono);max-width:38em}
footer{border-top:1px solid var(--line);padding:1.4rem 0 2.6rem;color:var(--ink2);font-size:.93rem}
footer p{max-width:none;margin:0 0 .5rem}
@media (prefers-reduced-motion:reduce){.strip .trace,.strip .flash{animation:none}html{scroll-behavior:auto}}
@media print{.lang,.cta{display:none}.sky{background:#0c2c66;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
'''

JS = r'''
(function(){var d=document.documentElement,ok=["en","kk","ru"],T=%TITLES%;
function set(l,save){if(ok.indexOf(l)<0)return;d.setAttribute("data-lang",l);d.lang=l;document.title=T[l];
var b=document.querySelectorAll(".lang button");for(var i=0;i<b.length;i++)b[i].setAttribute("aria-pressed",String(b[i].getAttribute("data-set")===l));
if(save){try{localStorage.setItem("sunpoint_lang",l)}catch(e){}}}
var q=(location.search.match(/[?&]lang=(en|kk|ru)/)||[])[1],s=null;try{s=localStorage.getItem("sunpoint_lang")}catch(e){}
var n=(navigator.language||"").slice(0,2).toLowerCase();if(ok.indexOf(n)<0)n=null;
set(q||s||n||d.getAttribute("data-lang"),false);
document.querySelector(".lang").addEventListener("click",function(e){var b=e.target.closest?e.target.closest("button"):null;if(b)set(b.getAttribute("data-set"),true)});
})();
'''


def bars(title_key, rows, note_key=None):
    """rows: (label_key, value_html, width_percent, css_class)"""
    out = [f'<figure class="bars"><h3>{t(title_key)}</h3>']
    for lab, val, w, cls in rows:
        out.append(f'<div class="row"><span class="lab">{t(lab)}</span><span class="val">{val}</span>'
                   f'<span class="bar"><i class="{cls}" style="width:{w:.1f}%"></i></span></div>')
    if note_key:
        out.append(f'<p class="note">{t(note_key)}</p>')
    out.append('</figure>')
    return "".join(out)


def page(host, deflang):
    base = f"https://{host}/sunpoint/"
    titles = "{" + ",".join(f'"{l}":"SunPoint — {tr("title", l)}"' for l in LANGS) + "}"
    ledger = "".join(f'<div class="{st}"><dt>{t(q)}</dt><dd class="v">{t(v)}</dd><dd class="w">{t(w)}</dd></div>'
                     for q, v, w, st in [("q1", "v1", "w1", "ok"), ("q2", "v2", "w2", "half"), ("q3", "v3", "w3", "ok"), ("q4", "v4", "w4", "half")])
    built = "".join(f'<li><b>{t(f"b{i}_t")}</b> {t(f"b{i}")}</li>' for i in range(1, 8))
    states = ["ok", "half", "half", "half", "no", "half", "ok", "na"]
    chk = "".join(f'<div class="{st}"><div class="c">{t(f"c{i}")}</div><div class="m">{t(f"m{i}")}</div><div class="r">{t(f"r{i}")}</div></div>'
                  for i, st in enumerate(states, 1))
    ch1 = bars("ch1_t", [("ch1_a", "30", 100, ""), ("ch1_b", "14", 46.7, ""), ("ch1_c", "≈10", 33.3, "")], "ch1_n")
    ch2 = bars("ch2_t", [("ch2_a", "6", 100, ""), ("ch2_b", "5", 83.3, ""), ("ch2_c", "1", 16.7, ""), ("ch2_d", "1", 16.7, ""),
                         ("ch2_e", "6", 100, "g"), ("ch2_f", "0", 0, "")])
    ch3 = bars("ch3_t", [("ch3_a", num("0.62", "0,62"), 100, "g"), ("ch3_b", num("0.54", "0,54"), 87.1, "g"),
                         ("ch3_c", num("0.40", "0,40"), 64.5, ""), ("ch3_d", num("0.35", "0,35"), 56.5, "t")])
    alt = "".join(f'<link rel="alternate" hreflang="{l}" href="{base}?lang={l}">' for l in LANGS)
    review_links = "".join(f'<a class="a2" data-l="{l}" lang="{l}" href="{REVIEW[l]}">{esc(tr("btn_review", l))}</a>' for l in LANGS)
    code_links = "".join(f'<a class="a1" data-l="{l}" lang="{l}" href="{REPO}">{esc(tr("btn_code", l))}</a>' for l in LANGS)
    lang_btns = "".join(f'<button type="button" data-set="{l}" aria-pressed="{"true" if l == deflang else "false"}">{LANG_NAME[l]}</button>' for l in LANGS)
    return f'''<!doctype html>
<html lang="{deflang}" data-lang="{deflang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SunPoint — {esc(tr("title", deflang))}</title>
<meta name="description" content="{html.escape(tr("meta_desc", deflang))}">
<link rel="canonical" href="{base}">
{alt}<link rel="alternate" hreflang="x-default" href="{base}">
<meta property="og:type" content="article">
<meta property="og:title" content="SunPoint — {html.escape(tr("title", deflang))}">
<meta property="og:description" content="{html.escape(tr("meta_desc", deflang))}">
<meta property="og:url" content="{base}">
<meta property="og:image" content="{base}assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preload" href="assets/bitter.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="assets/sourcesans3.woff2" as="font" type="font/woff2" crossorigin>
<style>{CSS}</style>
</head>
<body>
<header class="sky">
  <div class="wrap">
    <div class="top"><a class="mark" href="{REPO}"><i></i>SunPoint</a><nav class="lang" aria-label="Language">{lang_btns}</nav></div>
    <h1>{t("title")}</h1>
    <p class="sub">{t("sub")}</p>
    <p class="where">{t("where")}</p>
    <p class="byline">{t("byline")}</p>
    <div class="cta">{code_links}{review_links}</div>
    <figure class="moment">{strip_svg()}<figcaption id="stripcap">{t("fig_cap")}</figcaption></figure>
  </div>
  <svg class="clouds" viewBox="0 0 1200 100" preserveAspectRatio="none" aria-hidden="true"><path fill="#fff" transform="scale(1.093 1)" d="M0 100V62c40-22 86-26 128-10 26-30 78-42 124-22 30-26 84-30 122-6 34-20 82-18 116 6 40-24 96-22 134 6 30-22 78-24 112-2 36-28 96-30 138-2 34-18 78-14 108 8 40-22 92-16 118 12v48z"/><path fill="#fff" opacity=".35" d="M0 100V70c50-30 104-30 150-8 50-34 120-30 170 2 44-26 104-22 146 8 52-30 122-24 168 10 44-28 110-26 152 6 50-30 122-22 164 14 40-22 96-20 130 4 36-16 84-12 120 6v-12 0z"/></svg>
</header>
<main class="wrap">
  <p class="lede">{t("lede")}</p>

  <h2>{t("h_short")}</h2>
  <dl class="ledger">{ledger}</dl>

  <h2>{t("h_aware")}</h2>
  <p>{t("aware_p1")}</p>
  <p class="formula">{t("formula")}</p>
  <blockquote class="say"><p>{t("quote")}</p><cite>{t("quote_by")}</cite></blockquote>
  <p>{t("levels")}</p>

  <h2>{t("h_inh")}</h2>
  <p>{t("inh_p1")}</p>
  <ul class="heirs"><li><b>{t("inh1_t")}</b>{t("inh1")}</li><li><b>{t("inh2_t")}</b>{t("inh2")}</li><li><b>{t("inh3_t")}</b>{t("inh3")}</li></ul>

  <h2>{t("h_built")}</h2>
  <ul>{built}</ul>
  <p>{t("first_p")}</p>
  <p class="machine">{t("first_q")}</p>
  <p>{t("voice_p")}</p>
  <p class="machine">{t("voice_q")}</p>

  <h2>{t("h_check")}</h2>
  <p>{t("check_p")}</p>
  <div class="chk">{chk}</div>
  {ch1}
  <div class="pair">{ch2}{ch3}</div>
  <h3>{t("err_t")}</h3>
  <p>{t("err")}</p>
  <h3>{t("who_t")}</h3>
  <p>{t("who")}</p>

  <h2>{t("h_not")}</h2>
  <ul><li>{t("n1")}</li><li>{t("n2")}</li><li>{t("n3")}</li></ul>
  <h3>{t("h_ref")}</h3>
  <ol><li>{t("f1")}</li><li>{t("f2")}</li><li>{t("f3")}</li></ol>

  <h2>{t("h_word")}</h2>
  <blockquote class="word"><p>{t("word")}</p></blockquote>

  <h2>{t("h_next")}</h2>
  <ul><li>{t("x1")}</li><li>{t("x2")}</li><li>{t("x3")}</li></ul>

  <h2>{t("h_try")}</h2>
  <p>{t("try_p")}</p>
  <pre><code>git clone {REPO} &amp;&amp; cd sunpoint/src
SPIKE_AT=40 python3 -I sunpoint.py --test 120
cat window/first_voice.md</code></pre>
  <p>{t("try_q")} <a href="{REPO}/issues">{REPO.replace("https://", "")}/issues</a></p>
</main>
<footer><div class="wrap"><p>{t("foot")}</p><p>{t("fonts")}</p></div></footer>
<script>{JS.replace("%TITLES%", titles)}</script>
</body>
</html>
'''


# ---------------------------------------------------------------- article (Markdown)
def article(l):
    g = lambda k: tr(k, l)
    dec = (lambda s: s) if l == "en" else (lambda s: s.replace(".", ","))
    L = []
    L += [f"# {g('title')}", "", f"*{g('sub')}*", "", f"*{g('byline')}*", "", f"**{g('where')}** {g('lede')}", ""]
    L += [f"## {g('h_short')}", "", "| | | |", "|---|---|---|"]
    L += [f"| {g(f'q{i}')} | **{g(f'v{i}')}** | {g(f'w{i}')} |" for i in range(1, 5)]
    L += ["", f"## {g('h_aware')}", "", g("aware_p1"), "", f"> {g('formula')}", "", f"{g('quote')} — {g('quote_by')}", "", g("levels"), ""]
    L += [f"## {g('h_inh')}", "", g("inh_p1"), ""]
    L += [f"- **{g(f'inh{i}_t')}.** {g(f'inh{i}')}" for i in range(1, 4)]
    L += ["", f"## {g('h_built')}", ""]
    L += [f"- **{g(f'b{i}_t')}** {g(f'b{i}')}" for i in range(1, 8)]
    L += ["", f"{g('first_p')} «{g('first_q')}»" if l != "en" else f"{g('first_p')} \"{g('first_q')}\"", ""]
    L += [f"{g('voice_p')} «{g('voice_q')}»" if l != "en" else f"{g('voice_p')} \"{g('voice_q')}\"", ""]
    L += [f"## {g('h_check')}", "", g("check_p"), "", f"| {g('c_claim')} | {g('c_meas')} | {g('c_verd')} |", "|---|---|---|"]
    L += [f"| {g(f'c{i}')} | {g(f'm{i}')} | **{g(f'r{i}')}** |" for i in range(1, 9)]
    L += ["", f"**{g('ch1_t')}:** {g('ch1_a')} — 30; {g('ch1_b')} — 14; {g('ch1_c')} — ≈10. {g('ch1_n')}", ""]
    L += [f"**{g('ch2_t')}:** {g('ch2_a')} — 6; {g('ch2_b')} — 5; {g('ch2_c')} — 1; {g('ch2_d')} — 1; {g('ch2_e')} — 6; {g('ch2_f')} — 0.", ""]
    L += [f"**{g('ch3_t')}:** {g('ch3_a')} — {dec('0.62')}; {g('ch3_b')} — {dec('0.54')}; {g('ch3_c')} — {dec('0.40')}; {g('ch3_d')} — {dec('0.35')}.", ""]
    L += [f"**{g('err_t')}.** {g('err')}", "", f"**{g('who_t')}.** {g('who')}", ""]
    L += [f"## {g('h_not')}", "", f"- {g('n1')}", f"- {g('n2')}", f"- {g('n3')}", "", f"**{g('h_ref')}:**", "", f"1. {g('f1')}", f"2. {g('f2')}", f"3. {g('f3')}", ""]
    L += [f"## {g('h_word')}", "", g("word"), ""]
    L += [f"## {g('h_next')}", "", f"- {g('x1')}", f"- {g('x2')}", f"- {g('x3')}", ""]
    L += [f"## {g('h_try')}", "", g("try_p"), "", "```bash", f"git clone {REPO} && cd sunpoint/src", "SPIKE_AT=40 python3 -I sunpoint.py --test 120",
          "cat window/first_voice.md", "```", "", f"{g('try_q')} {REPO}/issues", ""]
    rev = "REVIEW_2026-11-23.md" if l == "en" else "REVIEW_2026-11-23.ru.md"
    L += [f"**GitHub:** [{REPO.replace('https://', '')}]({REPO})  ", f"**{g('btn_review')}:** [docs/{rev}]({rev})  ",
          "**Web:** [sun-agi.com/sunpoint](https://sun-agi.com/sunpoint/) · [galymzhan.kz/sunpoint](https://galymzhan.kz/sunpoint/)", "", f"*{g('foot')}*", ""]
    return "\n".join(L)


def main():
    for host, deflang in SITES:
        out = os.path.join(HERE, "dist", host, "sunpoint")
        os.makedirs(os.path.join(out, "assets"), exist_ok=True)
        with open(os.path.join(out, "index.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(page(host, deflang))
        for name in os.listdir(os.path.join(HERE, "assets")):
            if name.startswith("og-"):
                continue
            shutil.copy2(os.path.join(HERE, "assets", name), os.path.join(out, "assets", name))
        og = os.path.join(HERE, "assets", f"og-{deflang}.png")          # the share picture in the site's default language
        if os.path.exists(og):
            shutil.copy2(og, os.path.join(out, "assets", "og.png"))
        print("page:", os.path.relpath(out, ROOT))
    for l in LANGS:
        p = os.path.join(ROOT, "docs", f"ARTICLE.{l}.md")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(article(l))
        print("article:", os.path.relpath(p, ROOT))


if __name__ == "__main__":
    main()
