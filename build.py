#!/usr/bin/env python3
"""Build the static Democratic Leadership Whip Tracker site.

Usage: python3 build.py [--site-url https://example.com] [--out _site]
Reads data/members.json, data/feed.json, data/meta.json. Writes a GitHub Pages-ready folder.
"""
import argparse, html, json, os, shutil, datetime
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--site-url", default=os.environ.get("SITE_URL", "https://example.github.io/whip-tracker"))
ap.add_argument("--out", default=os.path.join(HERE, "_site"))
args = ap.parse_args()
SITE = args.site_url.rstrip("/")
OUT = args.out

def load(name, default):
    p = os.path.join(HERE, "data", name)
    return json.load(open(p)) if os.path.exists(p) else default

members = load("members.json", [])
feed = load("feed.json", [])
meta = load("meta.json", {})
for m in members:
    m.pop("notes", None)  # private notes never go public
    for k, v in (("district", ""), ("faction", ""), ("status", "Incumbent"), ("since", None), ("stance", None), ("backing", ""),
                 ("confidence", ""), ("summary", ""), ("quote", ""), ("source", ""), ("sourceUrl", ""), ("date", ""), ("via", ""),
                 ("leaderPick", ""), ("changed", ""), ("candidate", False), ("history", [])):
        m.setdefault(k, v)

TODAY = datetime.date.today().isoformat()
LAST = (meta.get("lastRun") or TODAY)[:10]
e = lambda s: html.escape("" if s is None else str(s), quote=True)
def clip(t, n=155):
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[:n-1].rsplit(" ", 1)[0].rstrip(",.;:") + "…"

RACE = {
  "senate": dict(leader="Chuck Schumer", short="Schumer", challenger="Chris Van Hollen", chal_short="Van Hollen",
                 title="Senate Democratic leader race", vote="secret ballot of Senate Democrats on 1 December 2026",
                 needed="28 of 55 votes (29 if Mary Peltola's Alaska seat is called for her)",
                 labels={2:"Declared for Schumer",1:"Leaning Schumer",0:"Undecided",-1:"Leaning against Schumer",-2:"Opposed to Schumer"}),
  "house": dict(leader="Hakeem Jeffries", short="Jeffries", challenger=None, chal_short=None,
                title="House Speaker race", vote="House Democratic Caucus vote on 18 November 2026, then the full House floor vote on 3 January 2027",
                needed="a majority of members voting on the House floor (218 if all 435 vote)",
                labels={2:"Declared for Jeffries",1:"Leaning Jeffries",0:"Undecided",-1:"Leaning against Jeffries",-2:"Opposed to Jeffries"}),
}
PCT = {2:100,1:75,0:50,-1:25,-2:0}
COL = {2:"var(--s2)",1:"var(--s1)",0:"var(--s0)",-1:"var(--sm1)",-2:"var(--sm2)",None:"var(--snone)"}

def label(m):
    return "No public position" if m["stance"] is None else RACE[m["chamber"]]["labels"][m["stance"]]
def where(m):
    return m["state"] if m["chamber"] == "senate" else m["district"]
def role(m):
    return ("Senator" if m["status"] == "Incumbent" else "Senator-elect") if m["chamber"] == "senate" else ("Rep." if m["status"] == "Incumbent" else "Rep.-elect")
def fmt(d):
    try:
        return datetime.date.fromisoformat(d).strftime("%-d %B %Y")
    except Exception:
        return d or ""
def by(ch):
    return [m for m in members if m["chamber"] == ch]

def counts(ch):
    c = Counter(m["stance"] for m in by(ch))
    return {k: c.get(k, 0) for k in (2, 1, 0, -1, -2, None)}

def names(ms, root):
    return ", ".join(f'<a href="{root}members/{e(m["id"])}/">{e(m["name"])}</a> ({e(where(m))})' for m in sorted(ms, key=lambda x: x["name"].split()[-1])) or "None so far."

DOME = open(os.path.join(HERE, "static", "dome.svg")).read()

def head(title, desc, path, root, jsonld, noindex=False, race=""):
    url = SITE + path
    ld = "\n".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in jsonld)
    return f"""<!DOCTYPE html>
<html lang="en-GB" data-root="{root}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(clip(desc))}">
<meta name="theme-color" content="#14213d">
<link rel="alternate" type="application/rss+xml" title="Democratic Leadership Whip Tracker updates" href="{SITE}/feed.xml">
<link rel="canonical" href="{e(url)}">
{'<meta name="robots" content="noindex,follow">' if noindex else '<meta name="robots" content="index,follow,max-image-preview:large">'}
<meta property="og:type" content="website">
<meta property="og:site_name" content="Democratic Leadership Whip Tracker">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(clip(desc, 200))}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{SITE}/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(clip(desc, 200))}">
<meta name="twitter:image" content="{SITE}/og.png">
<link rel="icon" href="{root}favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&family=Libre+Caslon+Text:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}style.css">
{ld}
</head>
<body data-race="{race}">
<div class="wrap">"""

def mast(h1, sub, root, tabs=True):
    t = ""
    if tabs:
        t = f"""<div class="tabs" role="tablist" aria-label="Choose race">
        <button class="tab" role="tab" id="tab-senate" aria-selected="true" data-race="senate">Senate: Schumer vs Van Hollen</button>
        <button class="tab" role="tab" id="tab-house" aria-selected="false" data-race="house">House: Jeffries for Speaker</button>
      </div>"""
    return f"""  <header class="mast">
    {DOME}
    <div class="mast-inner">
      <div>
        <p class="eyebrow">120th Congress · Leadership elections · Unofficial whip count</p>
        <h1>{h1}</h1>
        <p class="sub">{sub}</p>
      </div>
      {t}
    </div>
    <div class="stars" aria-hidden="true">★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★</div>
  </header>
  <nav class="sitenav" aria-label="Site">
    <a href="{root}">Tracker</a><a href="{root}senate/">Senate: Schumer vs Van Hollen</a><a href="{root}house/">House: Jeffries for Speaker</a><a href="{root}faq/">FAQ</a><a href="{root}about/">How it works</a>
  </nav>"""

APP = """  <div id="banner" class="banner" hidden></div>
  <section class="card" aria-labelledby="sumtitle">
    <div class="sumhead"><h2 id="sumtitle">Where the caucus stands</h2><div class="meta" id="keymeta"></div></div>
    <div class="bar" id="bar" aria-label="Stance counts"></div>
    <div class="legend" id="legend"></div>
  </section>
  <div class="mainrow">
    <section class="card" aria-labelledby="hemititle">
      <h2 id="hemititle">Seat map</h2>
      <svg id="hemi" viewBox="0 0 800 432" role="img" aria-label="Hemicycle of members coloured by stance"></svg>
      <p class="note">Each dot is a member, grouped by stance. Hover for detail, click to jump to their row. In the Senate, a dot with a hollow centre marks someone who has named Van Hollen.</p>
    </section>
    <section class="card" aria-labelledby="feedtitle">
      <h2 id="feedtitle">Latest activity</h2>
      <div class="feed" id="feed"><div class="empty">Loading…</div></div>
    </section>
  </div>
  <section class="card" aria-labelledby="gridtitle">
    <h2 id="gridtitle">Every member</h2>
    <div class="filters">
      <input id="q" type="search" placeholder="Search name, state or district" aria-label="Search members">
      <select id="fStance" aria-label="Filter by stance"></select>
      <select id="fStatus" aria-label="Filter by status"><option value="">All statuses</option><option>Incumbent</option><option>New</option><option>Returning</option><option>Race not called</option><option>Leaving</option></select>
      <select id="fConf" aria-label="Filter by confidence"><option value="">Any confidence</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
      <select id="fFaction" aria-label="Filter by faction"><option value="">All factions</option></select>
      <span class="count" id="count"></span>
    </div>
    <div class="tablewrap"><table><thead><tr id="thead"></tr></thead><tbody id="tbody"><tr><td class="empty" colspan="12">Loading members…</td></tr></tbody></table></div>
    <p class="note" id="status"></p>
  </section>"""

def foot(root):
    return f"""  <footer class="foot">Unofficial tracker built from public reporting. Not affiliated with the US Congress or either party. Data last checked {e(fmt(LAST))}. <a href="{root}about/">How it works</a> · <a href="{root}faq/">FAQ</a></footer>
</div>
<div class="tip" id="tip" role="tooltip"></div>
<script src="{root}app.js" defer></script>
</body>
</html>"""

def foot_static(root):
    return f"""  <footer class="foot">Unofficial tracker built from public reporting. Not affiliated with the US Congress or either party. Data last checked {e(fmt(LAST))}. <a href="{root}about/">How it works</a> · <a href="{root}faq/">FAQ</a></footer>
</div>
</body>
</html>"""

def race_summary(ch, root):
    r = RACE[ch]; c = counts(ch); ms = by(ch)
    groups = [(s, [m for m in ms if m["stance"] == s]) for s in (2, 1, 0, -1, -2)]
    out = [f'<section class="card seo" aria-labelledby="seo-{ch}"><h2 id="seo-{ch}">{e(r["title"])}: the full list</h2>']
    lead = c[2] + c[1]
    if ch == "senate":
        vh = [m for m in ms if m["backing"] == "Van Hollen"]
        out.append(f'<p>{e(r["leader"])} is seeking another term as Senate Democratic leader and {e(r["challenger"])} is challenging him. '
                   f'The leader is chosen by {e(r["vote"])}, and the winner needs {e(r["needed"])}. '
                   f'As of {e(fmt(LAST))}, {c[2]} senators have publicly declared for Schumer and {c[1]} lean his way. '
                   f'{len(vh)} have named Van Hollen, {c[-2]+c[-1]} in total oppose or lean against Schumer, {c[0]} say they are undecided and {c[None]} have said nothing publicly.</p>')
    else:
        out.append(f'<p>{e(r["leader"])} is running for Speaker of the House. No challenger has formally declared. '
                   f'The decisive steps are the {e(r["vote"])}, where he needs {e(r["needed"])}. '
                   f'As of {e(fmt(LAST))}, {c[2]} House Democrats have publicly declared for Jeffries and {c[1]} lean his way. '
                   f'{c[-1]+c[-2]} oppose or lean against him, {c[0]} are publicly uncommitted and {c[None]} have not said anything publicly.</p>')
    for s, g in groups:
        out.append(f'<h3><i class="sw" style="background:{COL[s]}"></i>{e(r["labels"][s])} ({len(g)})</h3><p class="namelist">{names(g, root)}</p>')
    nog = [m for m in ms if m["stance"] is None]
    out.append(f'<details><summary>No public position yet ({len(nog)})</summary><p class="namelist">{names(nog, root)}</p></details>')
    out.append("</section>")
    return "\n".join(out)

def faq_items():
    s, h = by("senate"), by("house")
    vh = [m["name"] for m in s if m["backing"] == "Van Hollen" and not m["candidate"]]
    sch = [m["name"] for m in s if m["stance"] == 2 and not m["candidate"]]
    agst = [m["name"] for m in s if m["stance"] in (-1, -2) and m["backing"] != "Van Hollen" and not m["candidate"]]
    hag = [m["name"] for m in h if m["stance"] in (-1, -2)]
    hund = [m for m in h if m["stance"] == 0]
    cs, ch = counts("senate"), counts("house")
    j = lambda xs: ", ".join(xs) if xs else "none so far"
    return [
      ("Who is challenging Chuck Schumer for Senate Democratic leader?",
       "Senator Chris Van Hollen of Maryland is challenging Chuck Schumer for leader of the Senate Democrats in the new Congress."),
      ("When is the Senate Democratic leader vote?",
       "Senate Democrats are due to pick their leader by secret ballot on 1 December 2026."),
      ("How many votes does Schumer or Van Hollen need to win?",
       "The winner needs a majority of the Senate Democratic caucus: 28 of 55 votes, or 29 if Mary Peltola's Alaska race is called for her and the caucus grows to 56."),
      ("Which senators have endorsed Chris Van Hollen?",
       f"Senators and senators-elect who have publicly backed Van Hollen: {j(vh)}."),
      ("Which senators support Chuck Schumer as leader?",
       f"{cs[2]} senators, including Schumer, have publicly declared for him. Besides Schumer, they are: {j(sch)}."),
      ("Which senators oppose Schumer but haven't backed Van Hollen?",
       f"These senators or senators-elect have said they oppose Schumer, or lean against him, without naming Van Hollen: {j(agst)}."),
      ("How many Democratic senators are undecided?",
       f"{cs[0]} have said publicly they are undecided, and {cs[None]} have made no public statement that we have found."),
      ("Is anyone challenging Hakeem Jeffries for Speaker?",
       "No House Democrat has formally declared against Hakeem Jeffries. Some members have floated alternatives, and a few have set conditions for their support."),
      ("When is the vote for Speaker of the House?",
       "House Democrats hold their internal caucus vote on 18 November 2026. The full House elects the Speaker on 3 January 2027, when the new Congress meets."),
      ("Which House Democrats won't back Jeffries?",
       f"Members who have said they oppose Jeffries or set conditions on their vote: {j(hag)}. {len(hund)} more are publicly uncommitted."),
      ("How many House Democrats support Jeffries for Speaker?",
       f"{ch[2]} House Democrats have publicly declared for Jeffries and {ch[1]} lean his way. {ch[None]} have not said anything publicly."),
      ("Is the leadership vote secret?",
       "Yes. Both parties choose their Senate leaders by secret ballot, so this tracker shows public statements and reporting, not actual votes."),
      ("How is this tracker updated?",
       "News sources are checked every hour. A stance changes only when there is a dated, named source, such as the member's own words or a report from a reputable outlet."),
    ]

def write(path, content):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w").write(content)

if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)
for f in ("style.css", "app.js", "favicon.svg"):
    shutil.copy(os.path.join(HERE, "static", f), os.path.join(OUT, f))
def make_og(path):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return
    import glob
    def font(names, size):
        for n in names:
            for p in glob.glob(f"/usr/share/fonts/**/{n}", recursive=True):
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), (20, 33, 61)); d = ImageDraw.Draw(im)
    serif = font(["DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"], 62); sans = font(["DejaVuSans.ttf", "LiberationSans-Regular.ttf"], 28); small = font(["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"], 22)
    brass, cream = (201, 169, 90), (246, 241, 227)
    d.rectangle([0, H - 10, W, H], fill=brass)
    d.text((70, 70), "120TH CONGRESS · UNOFFICIAL WHIP COUNT", font=small, fill=brass)
    d.text((70, 115), "Democratic Leadership", font=serif, fill=cream); d.text((70, 190), "Whip Tracker", font=serif, fill=cream)
    d.text((70, 285), "Schumer vs Van Hollen · Jeffries for Speaker", font=sans, fill=(214, 208, 190))
    cols = {-2: (184, 68, 31), -1: (232, 149, 90), 0: (201, 162, 39), None: (201, 205, 212), 1: (122, 165, 216), 2: (29, 79, 145)}
    s_ = by("senate"); c_ = Counter(x["stance"] for x in s_); xx = 70
    for k in (-2, -1, 0, None, 1, 2):
        ww = round(1060 * c_[k] / max(1, len(s_))); d.rectangle([xx, 390, xx + ww, 436], fill=cols[k]); xx += ww
    d.text((70, 452), "Where every Senate Democrat stands on the leader race, updated hourly", font=sans, fill=(214, 208, 190))
    im.save(path, optimize=True)
make_og(os.path.join(OUT, "og.png"))
json.dump({"members": members, "feed": feed[:300], "meta": meta, "built": TODAY}, open(os.path.join(OUT, "data.json"), "w"), ensure_ascii=False, separators=(",", ":"))

WEBSITE = {"@context": "https://schema.org", "@type": "WebSite", "name": "Democratic Leadership Whip Tracker", "url": SITE + "/"}
def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + p} for i, (n, p) in enumerate(items)]}
def dataset(name, desc, path):
    return {"@context": "https://schema.org", "@type": "Dataset", "name": name, "description": desc, "url": SITE + path,
            "dateModified": LAST, "isAccessibleForFree": True, "creator": {"@type": "Organization", "name": "Democratic Leadership Whip Tracker"},
            "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": SITE + "/data.json"}]}
FAQ = faq_items()
faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}
def faq_html(items):
    return "\n".join(f'<details class="faq" open><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in items)

sitemap = []

# Home
cs, ch = counts("senate"), counts("house")
desc = (f"Live whip count: where every Democrat stands on Schumer vs Van Hollen and Jeffries for Speaker. "
        f"{cs[2]+cs[1]} senators back Schumer, {cs[-2]+cs[-1]} oppose. Updated hourly.")
write("index.html", head("Schumer vs Van Hollen Whip Count & Jeffries Speaker Tracker", desc, "/", "./",
      [WEBSITE, dataset("Democratic leadership race stances, 120th Congress", desc, "/")])
      + mast("Democratic Leadership Whip Tracker", "Where every Democrat in the incoming Senate and House publicly stands in the leadership races. Built from public statements only: the leader votes are secret ballots.", "./")
      + APP + race_summary("senate", "./") + race_summary("house", "./")
      + f'<section class="card seo"><h2>Common questions</h2>{faq_html(FAQ[:6])}<p><a href="./faq/">More questions and answers</a></p></section>'
      + foot("./"))
ALLD = max([m["date"] for m in members if m["date"]] + [LAST])
sitemap.append(("/", "1.0", ALLD))

# Race pages
for chm, path, t, h1, d in (
    ("senate", "/senate/", "Schumer vs Van Hollen Whip Count: Every Senate Democrat",
     "Schumer vs Van Hollen: Senate Democratic leader whip count",
     f"Who supports Chuck Schumer and who backs Chris Van Hollen for Senate Democratic leader? {cs[2]} declared for Schumer, {len([m for m in by('senate') if m['backing']=='Van Hollen'])} named Van Hollen. Live count, updated hourly."),
    ("house", "/house/", "Jeffries Speaker Whip Count: Every House Democrat's Stance",
     "Hakeem Jeffries for Speaker: House Democrat whip count",
     f"Which House Democrats back Hakeem Jeffries for Speaker and who is holding out? {ch[2]} declared for Jeffries, {ch[0]} uncommitted. Live count, updated hourly.")):
    write(path.strip("/") + "/index.html",
          head(t, d, path, "../", [WEBSITE, crumbs([("Tracker", "/"), (RACE[chm]["title"], path)]), dataset(RACE[chm]["title"] + " stances", d, path)], race=chm)
          + mast(h1, d, "../", tabs=False) + APP + race_summary(chm, "../")
          + f'<section class="card seo"><h2>Questions about this race</h2>{faq_html([x for x in FAQ if (("Jeffries" in x[0] or "House" in x[0] or "Speaker" in x[0]) if chm=="house" else not ("Jeffries" in x[0] or "House" in x[0] or "Speaker" in x[0]))])}</section>'
          + foot("../"))
    sitemap.append((path, "0.9", max([m["date"] for m in by(chm) if m["date"]] + [LAST])))

# FAQ
write("faq/index.html", head("Schumer, Van Hollen and Jeffries Leadership Race FAQ", "Answers on the Senate Democratic leader vote between Chuck Schumer and Chris Van Hollen, and Hakeem Jeffries' bid for Speaker: dates, votes needed and who backs whom.",
      "/faq/", "../", [WEBSITE, crumbs([("Tracker", "/"), ("FAQ", "/faq/")]), faq_ld])
      + mast("Questions about the Democratic leadership races", "Dates, rules and who backs whom, generated from the latest tracker data.", "../", tabs=False)
      + f'<section class="card seo">{faq_html(FAQ)}</section>' + foot_static("../"))
sitemap.append(("/faq/", "0.8", ALLD))

# About
about = f"""<section class="card seo"><h2>How the tracker works</h2>
<p>This is an independent, unofficial tracker of public positions in two Democratic leadership races in the 120th Congress: the Senate Democratic leader race between Chuck Schumer and Chris Van Hollen, and Hakeem Jeffries' bid to become Speaker of the House.</p>
<h3>The five-point scale</h3>
<p>Each member is placed on a scale relative to the incumbent leader (Schumer in the Senate, Jeffries in the House). Declared for (100%), leaning for (75%), undecided (50%), leaning against (25%) and opposed (0%). The percentage is how far a member sways towards the leader. Members with no public statement are shown separately in grey.</p>
<h3>Sources and confidence</h3>
<p>Stances come from members' own statements and reporting by named outlets. Confidence is high for a member's own on-record words, medium for a report by a reputable outlet, and low for anonymous sourcing or conflicting reports. Every row links to its source.</p>
<h3>Updates</h3>
<p>News sources are checked every hour. A stance changes only when there is a dated, linkable source that is newer than the evidence already shown. Where reports conflict, the stance is not flipped; the row is marked as conflicting instead.</p>
<h3>Limits</h3>
<p>Leadership elections are secret ballots. This tracker shows what members have said in public, not how they will vote. Faction labels are partial. Members in races that have not been called are included and marked.</p>
<p>Not affiliated with the US Congress, either party, or any campaign.</p></section>"""
write("about/index.html", head("How the Democratic Leadership Whip Tracker Works", "How stances are sourced, scored and updated in this unofficial tracker of the Schumer vs Van Hollen and Jeffries Speaker races.",
      "/about/", "../", [WEBSITE, crumbs([("Tracker", "/"), ("How it works", "/about/")])])
      + mast("How the tracker works", "Sources, scoring and update rules.", "../", tabs=False) + about + foot_static("../"))
sitemap.append(("/about/", "0.5", LAST))

# Member pages
for m in members:
    r = RACE[m["chamber"]]; lab = label(m); w = where(m); rl = role(m)
    racepath = "/senate/" if m["chamber"] == "senate" else "/house/"
    q = (f"Does {m['name']} support Chuck Schumer or Chris Van Hollen?" if m["chamber"] == "senate" else f"Will {m['name']} vote for Hakeem Jeffries for Speaker?")
    if m["stance"] is None:
        ans = f"{m['name']} has not taken a public position that we have found."
    else:
        ans = f"{lab}." + (f" Backing: {m['backing']}." if m["backing"] else "") + f" {m['summary']}"
    t = (f"{m['name']} on Schumer vs Van Hollen | Whip Count" if m["chamber"] == "senate"
         else f"{m['name']} on Jeffries for Speaker | Whip Count")
    d = f"{q} {ans}"[:300]
    hist = m.get("history") or []
    hist_html = ("<ol class='hist'>" + "".join(f"<li><b>{e(fmt(h.get('date')))}</b>: {e(h.get('fromLabel'))} to {e(h.get('toLabel'))}. {e(h.get('summary'))} " + (f"<a href='{e(h.get('url'))}' rel='noopener'>{e(h.get('source') or 'Source')}</a>" if h.get('url') else '') + "</li>" for h in reversed(hist)) + "</ol>") if hist else "<p class='note'>No changes recorded since tracking began on 16 November 2026.</p>"
    s = m["stance"]
    pill = f'<span class="stance"><span class="pct {"light" if s in (1,0,-1,None) else ""}" style="background:{COL[s]}">{"–" if s is None else str(PCT[s])+"%"}</span>{e(lab)}</span>'
    facts = [("Chamber", "Senate" if m["chamber"] == "senate" else "House of Representatives"), ("State" if m["chamber"] == "senate" else "District", w),
             ("Status", m["status"]), ("In Congress since", m["since"] or "New member"), ("Faction", m["faction"] or "–")]
    if m["chamber"] == "senate" and m["leaderPick"]:
        facts.append(("Leader's primary pick", m["leaderPick"]))
    src = (f'<a href="{e(m["sourceUrl"])}" rel="noopener">{e(m["source"] or "Source")}</a>' if m["sourceUrl"] else e(m["source"])) + (f" · {e(fmt(m['date']))}" if m["date"] else "") + (f" · via {e(m['via'])}" if m["via"] else "")
    same = [x for x in by(m["chamber"]) if x["stance"] == s and x["id"] != m["id"]][:12]
    body = f"""<section class="card seo member">
  <p class="crumbs"><a href="../../">Tracker</a> › <a href="../..{racepath}">{e(r['title'])}</a> › {e(m['name'])}</p>
  <h2>{e(q)}</h2>
  <p>{pill}{(' <span class="chip">Backing: ' + e(m['backing']) + '</span>') if m['backing'] else ''}{(' <span class="chip">' + e(m['confidence']) + ' confidence</span>') if m['confidence'] else ''}</p>
  <p class="lede">{e(ans)}</p>
  {('<blockquote>' + e(m['quote']) + '</blockquote>') if m['quote'] else ''}
  {('<p class="note">Source: ' + src + '</p>') if m['source'] else ''}
  <div class="dgrid">
    <div><h3>Member details</h3><dl class="facts">{''.join(f'<dt>{e(k)}</dt><dd>{e(v)}</dd>' for k, v in facts)}</dl></div>
    <div><h3>Stance history</h3>{hist_html}</div>
  </div>
  <h3>About the race</h3>
  <p>{'Chuck Schumer is seeking another term as Senate Democratic leader, challenged by Chris Van Hollen. The vote is a ' + e(r['vote']) + ', and the winner needs ' + e(r['needed']) + '.' if m['chamber']=='senate' else 'Hakeem Jeffries is running for Speaker of the House with no declared challenger. The key votes are the ' + e(r['vote']) + '.'} <a href="../..{racepath}">See where every {'senator' if m['chamber']=='senate' else 'House Democrat'} stands</a>.</p>
  <h3>Others with the same stance</h3><p class="namelist">{names(same, '../../')}</p>
</section>"""
    person = {"@context": "https://schema.org", "@type": "ProfilePage", "dateModified": m["date"] or LAST,
              "mainEntity": {"@type": "Person", "name": m["name"], "jobTitle": ("United States Senator" if m["chamber"] == "senate" else "Member of the US House of Representatives") + (" (elect)" if m["status"] not in ("Incumbent", "Leaving") else ""),
                             "affiliation": {"@type": "Organization", "name": "Democratic Party"}}}
    write(f"members/{m['id']}/index.html",
          head(t, d, f"/members/{m['id']}/", "../../", [crumbs([("Tracker", "/"), (r["title"], racepath), (m["name"], f"/members/{m['id']}/")]), person, {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}}]}],
               noindex=(m["stance"] is None))
          + mast(e(m["name"]), f"{e(rl)}, {e(w)}. {e(lab)}.", "../../", tabs=False) + body + foot_static("../../"))
    if m["stance"] is not None:
        sitemap.append((f"/members/{m['id']}/", "0.6", m["date"] or LAST))

# 404, robots, sitemap, .nojekyll
R404 = SITE + "/"
write("404.html", head("Page not found | Democratic Leadership Whip Tracker", "Page not found.", "/404.html", R404, [], noindex=True)
      + mast("Page not found", "That page doesn't exist. Try the tracker instead.", R404, tabs=False) + f'<p><a href="{R404}">Back to the tracker</a></p>' + foot_static(R404))
write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
      + "".join(f"  <url><loc>{e(SITE + p)}</loc><lastmod>{lm}</lastmod><changefreq>daily</changefreq><priority>{pr}</priority></url>\n" for p, pr, lm in sitemap) + "</urlset>\n")
# RSS feed of latest stance activity
from email.utils import format_datetime
def rfc(d):
    try:
        return format_datetime(datetime.datetime.combine(datetime.date.fromisoformat(d), datetime.time(12), tzinfo=datetime.timezone.utc))
    except Exception:
        return format_datetime(datetime.datetime.now(datetime.timezone.utc))
items = []
for ev in feed[:50]:
    link = f"{SITE}/members/{ev.get('memberId','')}/"
    title = f"{ev.get('name','')} ({ev.get('where','')}): {ev.get('head','')}"
    body = (ev.get("text") or "") + (f" Source: {ev.get('source')}." if ev.get("source") else "")
    items.append(f"<item><title>{e(title)}</title><link>{e(link)}</link><guid isPermaLink=\"false\">{e(ev.get('memberId',''))}-{e(ev.get('date',''))}-{e(ev.get('head',''))}</guid><pubDate>{rfc(ev.get('date',''))}</pubDate><description>{e(body)}</description></item>")
write("feed.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>Democratic Leadership Whip Tracker updates</title><link>{SITE}/</link><description>New and changed public stances in the Schumer vs Van Hollen and Jeffries Speaker races.</description><language>en-gb</language>{"".join(items)}</channel></rss>\n')
write(".nojekyll", "")
cname = os.environ.get("CNAME_DOMAIN")
if cname:
    write("CNAME", cname + "\n")
print(f"Built {len(sitemap)} indexable pages, {len(members)} member pages into {OUT}")
