"""
Script 01: Analyze Raw PeerRead Dataset
Phase 1 - Raw Exploration

Crawls: C:/Users/Document/OneDrive/Desktop/TFG/Dataset/PeerRead/data
Structure: {conference}/{split=train|dev|test}/{pdfs|reviews|parsed_pdfs}/

Counts physical PDFs and JSON review files per conference venue (summed across splits).
Outputs:
  - docs/diagrams/dataset_preparation/raw_files_per_conference.png  (bar chart)
  - docs/diagrams/dataset_preparation/physical_pdf_percentage.png   (pie chart)

Run from project root:
    python packages/dataset/scripts/01_analyze_raw_dataset.py
"""

import os
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT  = pathlib.Path(__file__).resolve().parents[3]
PEERREAD_ROOT = pathlib.Path(r"C:\Users\Document\OneDrive\Desktop\TFG\Dataset\PeerRead\data")
OUTPUT_DIR    = PROJECT_ROOT / "docs" / "diagrams" / "dataset_preparation"

os.makedirs(OUTPUT_DIR, exist_ok=True)

SPLITS = {"train", "dev", "test"}

print(f"[01] Crawling: {PEERREAD_ROOT}")

conference_stats = {}   # { conference_name: {"pdfs": int, "json": int, "other": int} }

for conf_dir in sorted(PEERREAD_ROOT.iterdir()):
    if not conf_dir.is_dir():
        continue
    conf_name = conf_dir.name
    conference_stats[conf_name] = {"pdfs": 0, "json": 0, "other": 0}

    for split_dir in conf_dir.iterdir():
        if not split_dir.is_dir() or split_dir.name not in SPLITS:
            continue
        for f in split_dir.rglob("*"):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            if ext == ".pdf":
                conference_stats[conf_name]["pdfs"] += 1
            elif ext == ".json":
                conference_stats[conf_name]["json"] += 1
            else:
                conference_stats[conf_name]["other"] += 1

# Remove conferences with zero files (e.g. nips_2013-2017 that only has README)
conference_stats = {k: v for k, v in conference_stats.items()
                    if v["pdfs"] + v["json"] + v["other"] > 0}

if not conference_stats:
    print("[01] WARNING: No data found under", PEERREAD_ROOT)
    raise SystemExit(1)

conferences = list(conference_stats.keys())
pdf_counts  = [conference_stats[c]["pdfs"]  for c in conferences]
json_counts = [conference_stats[c]["json"]  for c in conferences]

total_pdfs  = sum(pdf_counts)
total_json  = sum(json_counts)
total_other = sum(v["other"] for v in conference_stats.values())
total_all   = total_pdfs + total_json + total_other

print(f"\n[01] Conference breakdown:")
print(f"  {'Conference':<32} {'PDFs':>6}  {'JSONs':>6}")
print(f"  {'-'*47}")
for c in conferences:
    print(f"  {c:<32} {conference_stats[c]['pdfs']:>6}  {conference_stats[c]['json']:>6}")
print(f"  {'TOTAL':<32} {total_pdfs:>6}  {total_json:>6}")

x     = np.arange(len(conferences))
width = 0.35

fig, ax = plt.subplots(figsize=(max(10, len(conferences) * 2.0), 6))
bars_pdf  = ax.bar(x - width/2, pdf_counts,  width, label="Physical PDFs",
                   color="#3b82f6", edgecolor="white", linewidth=0.5)
bars_json = ax.bar(x + width/2, json_counts, width, label="Review/JSON files",
                   color="#f59e0b", edgecolor="white", linewidth=0.5)

ax.set_xticks(x)
ax.set_xticklabels([c.replace("_", "\n").replace("-", "‑\n", 1) for c in conferences], fontsize=9)
ax.set_xlabel("Conference Venue", fontsize=12, labelpad=10)
ax.set_ylabel("File Count", fontsize=12)
ax.set_title("PeerRead Raw Dataset — Files per Conference Venue",
             fontsize=14, fontweight="bold", pad=15)
ax.legend(fontsize=11)
ax.grid(axis="y", alpha=0.4, linestyle="--")

for bar in list(bars_pdf) + list(bars_json):
    h = bar.get_height()
    if h > 0:
        ax.text(bar.get_x() + bar.get_width()/2, h + 1, str(int(h)),
                ha="center", va="bottom", fontsize=8)

plt.tight_layout()
out1 = OUTPUT_DIR / "raw_files_per_conference.png"
plt.savefig(out1, dpi=150)
plt.close()
print(f"\n[01] Saved: {out1}")

non_pdf = total_all - total_pdfs
fig, ax = plt.subplots(figsize=(7, 7))
sizes   = [total_pdfs, non_pdf]
labels  = [f"Physical PDFs\n({total_pdfs})", f"Other Files\n({non_pdf})"]
colors  = ["#3b82f6", "#f59e0b"]
explode = (0.05, 0)

wedges, texts, autotexts = ax.pie(
    sizes, labels=labels, colors=colors, explode=explode,
    autopct="%1.1f%%", startangle=140, pctdistance=0.80,
    textprops={"fontsize": 12}
)
for at in autotexts:
    at.set_fontsize(13)
    at.set_fontweight("bold")

ax.set_title(
    f"Physical PDF Percentage in Raw PeerRead Dataset\n(Total files: {total_all})",
    fontsize=13, fontweight="bold", pad=20
)
plt.tight_layout()
out2 = OUTPUT_DIR / "physical_pdf_percentage.png"
plt.savefig(out2, dpi=150)
plt.close()
print(f"[01] Saved: {out2}")
print(f"\n[01] DONE — Total: {total_all}  |  PDFs: {total_pdfs} ({100*total_pdfs/total_all:.1f}%)")
