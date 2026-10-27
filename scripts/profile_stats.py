"""Render the committed public portfolio snapshot; use --refresh to collect anew."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "profile/portfolio-stats.json"
IMAGE = ROOT / "profile/portfolio-stats.svg"
OWNER = "alirafiqmalik"
PROJECTS = [
    "certified-confinement-acm-pqqs-26-artifacts",
    "ach-model-checking",
    "unity-hpc-controller",
    "agent-eval-hpc",
    "local-model-router",
    "esim-research-tools",
]


def collect():
    records = []
    for name in PROJECTS:
        url = f"https://api.github.com/repos/{OWNER}/{name}"
        with urlopen(url, timeout=30) as response:
            repo = json.load(response)
        if repo["private"] or repo["fork"]:
            raise ValueError(f"Expected a public, non-fork repository: {name}")
        with urlopen(url + "/languages", timeout=30) as response:
            languages = json.load(response)
        records.append({"repository": repo["full_name"], "source": url + "/languages", "languages": languages})
    return {"collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "repositories": records}


def render(snapshot):
    totals = Counter()
    for repo in snapshot["repositories"]:
        totals.update(repo["languages"])
    total = sum(totals.values())
    rows = totals.most_common(5)
    remainder = total - sum(value for _, value in rows)
    if remainder:
        rows.append(("Other", remainder))
    date = snapshot["collected_at"][:10]
    count = len(snapshot["repositories"])
    colors = ["#60a5fa", "#2dd4bf", "#c4b5fd", "#fbbf24", "#fb923c", "#94a3b8"]
    height = 100 + max(len(rows), 1) * 34
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="{height}" viewBox="0 0 640 {height}" role="img" aria-labelledby="title desc">',
             '<title id="title">Public portfolio · code composition</title>',
             f'<desc id="desc">Language bytes from {count} selected public repositories, collected {date} UTC.',
             escape("; ".join(f"{name}: {value / total:.1%}" for name, value in rows)) if total else "No language data.",
             '</desc>',
             f'<rect width="640" height="{height}" rx="14" fill="#0f172a"/>',
             '<g font-family="DejaVu Sans, Arial, sans-serif">',
             '<text x="24" y="33" fill="#f8fafc" font-size="20" font-weight="700">Public portfolio · code composition</text>',
             f'<text x="24" y="59" fill="#cbd5e1" font-size="13">{count} featured repositories · {date} UTC · language bytes</text>']
    for index, (name, value) in enumerate(rows):
        y = 94 + index * 34
        fraction = value / total
        parts.extend([
            f'<text x="24" y="{y}" fill="#e2e8f0" font-size="14">{escape(name)}</text>',
            f'<rect x="180" y="{y - 12}" width="350" height="10" rx="5" fill="#243247"/>',
            f'<rect x="180" y="{y - 12}" width="{350 * fraction:.2f}" height="10" rx="5" fill="{colors[index]}"/>',
            f'<text x="612" y="{y}" text-anchor="end" fill="#e2e8f0" font-size="14">{fraction:.1%}</text>',
        ])
    if not rows:
        parts.append('<text x="24" y="94" fill="#e2e8f0" font-size="14">No language data available</text>')
    parts.append('</g></svg>\n')
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch public GitHub metadata and language bytes")
    args = parser.parse_args()
    snapshot = collect() if args.refresh else json.loads(DATA.read_text())
    svg = render(snapshot)
    DATA.parent.mkdir(parents=True, exist_ok=True)
    if args.refresh:
        DATA.write_text(json.dumps(snapshot, indent=2) + "\n")
    IMAGE.write_text(svg)
    print(f"Rendered {IMAGE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
