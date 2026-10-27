"""Render local GitHub profile cards; use --refresh to collect public data."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "profile/portfolio-stats.json"
OWNER = "alirafiqmalik"
PROJECTS = [
    "certified-confinement-acm-pqqs-26-artifacts",
    "ach-model-checking",
    "unity-hpc-controller",
    "agent-eval-hpc",
    "local-model-router",
    "esim-research-tools",
]


def fetch(url):
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def collect():
    base = f"https://api.github.com/users/{OWNER}"
    profile = fetch(base)
    public = []
    page = 1
    while True:
        batch = fetch(f"{base}/repos?type=owner&per_page=100&page={page}")
        public.extend(repo for repo in batch if not repo["private"])
        if len(batch) < 100:
            break
        page += 1
    by_name = {repo["name"]: repo for repo in public}
    records = []
    for name in PROJECTS:
        repo = by_name[name]
        if repo["fork"]:
            raise ValueError(f"Expected a public, non-fork repository: {name}")
        url = f"https://api.github.com/repos/{OWNER}/{name}/languages"
        records.append({"repository": repo["full_name"], "source": url, "languages": fetch(url)})
    non_forks = [repo for repo in public if not repo["fork"]]
    return {
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "account": {
            "login": OWNER,
            "public_repositories": len(public),
            "non_fork_repositories": len(non_forks),
            "forks": len(public) - len(non_forks),
            "stars_on_non_forks": sum(repo["stargazers_count"] for repo in non_forks),
            "followers": profile["followers"],
            "sources": [base, f"{base}/repos?type=owner&per_page=100"],
        },
        "repositories": records,
    }


def render(snapshot, *, light=False, mobile=False):
    totals = Counter()
    for repo in snapshot["repositories"]:
        totals.update(repo["languages"])
    totals = Counter({name: count for name, count in totals.items() if count > 0})
    total = sum(totals.values())
    rows = totals.most_common(5)
    remainder = total - sum(value for _, value in rows)
    if remainder:
        rows.append(("Other", remainder))
    account = snapshot["account"]
    date = snapshot["collected_at"][:10]
    width, height = (420, 742) if mobile else (840, 490)
    bg, panel, border = ("#ffffff", "#f6f8fc", "#d9e2ef") if light else ("#0d1424", "#141f33", "#293850")
    fg, muted = ("#182b49", "#526681") if light else ("#edf4ff", "#a9bad3")
    accent = "#176caa" if light else "#73c8ff"
    colors = ["#3182ce", "#0d9488", "#8b5cf6", "#d49b18", "#e77734", "#64748b"]
    paths = [
        'M4 3h12v16H4z M7 3v16 M10 7h3 M10 10h3',
        'M7 4v9a4 4 0 0 0 4 4h4 M3 8l4-4 4 4 M12 14l3 3-3 3',
        'm10 2 2.5 5 5.5.8-4 4 .9 5.7-4.9-2.7-4.9 2.7.9-5.7-4-4L7.5 7z',
        'M13 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0 M3 18v-2a7 7 0 0 1 14 0v2',
    ]
    def label(x, y, value, size=14, color=fg, weight=400, extra=""):
        return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" {extra}>{escape(str(value))}</text>'

    summary = (f'{account["public_repositories"]} public repositories, '
               f'{account["non_fork_repositories"]} non-fork repositories, '
               f'{account["stars_on_non_forks"]} stars on non-forks, '
               f'{account["followers"]} followers. '
               f'Language bytes from {len(snapshot["repositories"])} selected public repositories. '
               + ("; ".join(f"{name}: {value / total:.1%}" for name, value in rows) if total else "No language data.")
               + f' Collected {date} UTC.')
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Ali Hamza Malik · GitHub overview</title>',
        f'<desc id="desc">{escape(summary)}</desc>',
        '<defs><linearGradient id="accent"><stop stop-color="#3182ce"/><stop offset="1" stop-color="#14b8a6"/></linearGradient></defs>',
        f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="20" fill="{bg}" stroke="{border}"/>',
        '<rect x="28" y="26" width="36" height="4" rx="2" fill="url(#accent)"/>',
        '<g font-family="DejaVu Sans, Arial, sans-serif">',
        label(28, 63, "GitHub overview", 25, weight=700),
        label(28, 88, f"@{account['login']} · Public work", 13, muted),
    ]
    if not mobile:
        parts += [label(812, 49, "SNAPSHOT", 10, accent, 700, 'text-anchor="end" letter-spacing="1.5"'),
                  label(812, 70, date + " UTC", 12, muted, extra='text-anchor="end"')]
    metrics = [
        ("Public repos", account["public_repositories"], f'{account["forks"]} forks included'),
        ("Non-forks", account["non_fork_repositories"], "Public repositories"),
        ("Stars", account["stars_on_non_forks"], "On public non-forks"),
        ("Followers", account["followers"], "GitHub community"),
    ]
    tile_width = 176 if mobile else 187
    for index, (title, count, note) in enumerate(metrics):
        col, row = (index % 2, index // 2) if mobile else (index, 0)
        x, y = 28 + col * (tile_width + 12), 112 + row * 128
        parts += [f'<rect x="{x}" y="{y}" width="{tile_width}" height="116" rx="12" fill="{panel}" stroke="{border}"/>',
                  f'<path d="{paths[index]}" transform="translate({x+14} {y+14})" fill="none" stroke="{accent}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
                  label(x+42, y+29, title, 13, muted, 600),
                  label(x+16, y+70, f"{count:,}", 30, weight=700),
                  label(x+16, y+96, note, 11, muted)]
    heading_y = 396 if mobile else 270
    parts += [label(28, heading_y, "Languages in selected projects", 17, weight=700),
              label(28, heading_y+22, f'{len(snapshot["repositories"])} repositories · Share of code bytes', 12, muted)]
    track_y, track_width = heading_y+38, width-56
    parts.append(f'<clipPath id="bar"><rect x="28" y="{track_y}" width="{track_width}" height="10" rx="5"/></clipPath>')
    parts.append(f'<rect x="28" y="{track_y}" width="{track_width}" height="10" rx="5" fill="{panel}"/>')
    offset = 28.0
    for index, (_, value) in enumerate(rows):
        segment = track_width * value / total
        parts.append(f'<rect x="{offset:.3f}" y="{track_y}" width="{segment:.3f}" height="10" fill="{colors[index]}" clip-path="url(#bar)"/>')
        offset += segment
    for index, (name, value) in enumerate(rows):
        col, row = (0, index) if mobile else (index % 2, index // 2)
        x, y = 28 + col*404, track_y+41+row*34
        row_width = 364 if mobile else 380
        parts += [f'<circle cx="{x+5}" cy="{y-5}" r="4" fill="{colors[index]}"/>',
                  label(x+19, y, name, 13),
                  label(x+row_width, y, f"{value/total:.1%}", 13, muted, 600, 'text-anchor="end"')]
    if not rows:
        parts.append(label(28, track_y+41, "No language data available", 13, muted))
    parts += [f'<path d="M28 {height-45}H{width-28}" stroke="{border}"/>',
              label(28, height-22, f"Updated {date} UTC" if mobile else "Public GitHub data · Updated weekly", 11, muted),
              label(width-28, height-22, "GitHub API" if mobile else f'{len(snapshot["repositories"])}-project language sample', 11, muted, extra='text-anchor="end"'),
              '</g></svg>\n']
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch public account metadata and language bytes")
    args = parser.parse_args()
    snapshot = collect() if args.refresh else json.loads(DATA.read_text())
    # Complete every rendering before changing the committed snapshot.
    images = {}
    for mobile in (False, True):
        for light in (False, True):
            suffix = ("-mobile" if mobile else "") + ("-light" if light else "")
            images[f"portfolio-stats{suffix}.svg"] = render(snapshot, light=light, mobile=mobile)
    DATA.parent.mkdir(parents=True, exist_ok=True)
    if args.refresh:
        DATA.write_text(json.dumps(snapshot, indent=2) + "\n")
    for name, svg in images.items():
        (DATA.parent / name).write_text(svg)
        print(f"Rendered profile/{name}")


if __name__ == "__main__":
    main()
