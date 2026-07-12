"""
Script 03: Analyze Sorted (Labeled) Dataset
Phase 1 - Post-Labeling Analysis

Reads: data/peerread_filtered/{accepted|rejected}/{conference}/pdfs/*.pdf
Structure produced by script 02.

Outputs stacked bar chart showing accepted vs rejected PDF counts per venue:
  docs/diagrams/dataset_preparation/labeled_pdfs_per_conference.png

Run from project root:
    python packages/dataset/scripts/03_analyze_sorted_dataset.py
"""

import os
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT  = pathlib.Path(__file__).resolve().parents[3]
PEERREAD_ROOT = PROJECT_ROOT / "data" / "peerread_filtered"    # output of script 02
OUTPUT_DIR    = PROJECT_ROOT / "docs" / "diagrams" / "dataset_preparation"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"[03] Scanning: {PEERREAD_ROOT}")

conference_stats = {}   # { conference_name: {"accepted": int, "rejected": int} }

for verdict in ("accepted", "rejected"):
    verdict_dir = PEERREAD_ROOT / verdict
    if not verdict_dir.exists():
        print(f"[03] WARNING: {verdict_dir} does not exist — run script 02 first.")
        continue
    for conf_dir in sorted(verdict_dir.iterdir()):
        if not conf_dir.is_dir():
            continue
        conf_name = conf_dir.name
        if conf_name not in conference_stats:
            conference_stats[conf_name] = {"accepted": 0, "rejected": 0}

        # Count physical PDFs in the pdfs/ subfolder
        pdfs_subdir = conf_dir / "pdfs"
        pdf_count   = len(list(pdfs_subdir.glob("*.pdf"))) if pdfs_subdir.exists() else 0
        conference_stats[conf_name][verdict] += pdf_count
        print(f"[03]   {verdict:8s} / {conf_name:20s} : {pdf_count} PDFs")

if not conference_stats:
    print("[03] WARNING: data/peerread_filtered is empty. Run script 02 first.")
    conference_stats = {"(empty — run script 02)": {"accepted": 0, "rejected": 0}}

conferences  = sorted(conference_stats.keys())
acc_counts   = [conference_stats[c]["accepted"] for c in conferences]
rej_counts   = [conference_stats[c]["rejected"] for c in conferences]
total_counts = [a + r for a, r in zip(acc_counts, rej_counts)]

x     = np.arange(len(conferences))
width = 0.55

fig, ax = plt.subplots(figsize=(max(9, len(conferences) * 2.5), 7))

bars_acc = ax.bar(x, acc_counts, width, label="Accepted", color="#10b981",
                  edgecolor="white", linewidth=0.5, zorder=3)
bars_rej = ax.bar(x, rej_counts, width, label="Rejected", color="#ef4444",
                  bottom=acc_counts, edgecolor="white", linewidth=0.5, zorder=3)

# White value labels inside bars
for bar, val in zip(bars_acc, acc_counts):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, val/2,
                str(val), ha="center", va="center",
                fontsize=12, color="white", fontweight="bold")

for bar, a_val, r_val in zip(bars_rej, acc_counts, rej_counts):
    if r_val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, a_val + r_val/2,
                str(r_val), ha="center", va="center",
                fontsize=12, color="white", fontweight="bold")

# Total label above each bar
for xi, total in zip(x, total_counts):
    ax.text(xi, total + max(total_counts)*0.02, f"n={total}",
            ha="center", va="bottom", fontsize=10, color="#374151", fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels([c.replace("_", "\n") for c in conferences], fontsize=12)
ax.set_xlabel("Conference Venue", fontsize=13, labelpad=10)
ax.set_ylabel("Number of PDFs", fontsize=13)
ax.set_title(
    "Labeled PDFs per Conference Venue\n(Accepted vs. Rejected)",
    fontsize=14, fontweight="bold", pad=15
)
ax.legend(fontsize=12, loc="upper right")
ax.grid(axis="y", alpha=0.35, linestyle="--", zorder=0)
ax.set_ylim(0, max(total_counts) * 1.2 + 5 if total_counts else 10)

plt.tight_layout()
out_path = OUTPUT_DIR / "labeled_pdfs_per_conference.png"
plt.savefig(out_path, dpi=150)
plt.close()

print(f"\n[03] Saved: {out_path}")

grand_acc = sum(acc_counts)
grand_rej = sum(rej_counts)
grand_tot = grand_acc + grand_rej
print()
print("=" * 55)
print(f"[03] DONE")
print(f"  {'Conference':<20} {'Accepted':>9} {'Rejected':>9} {'Total':>7}")
print(f"  {'-'*49}")
for c, a, r in zip(conferences, acc_counts, rej_counts):
    print(f"  {c:<20} {a:>9} {r:>9} {a+r:>7}")
print(f"  {'-'*49}")
print(f"  {'TOTAL':<20} {grand_acc:>9} {grand_rej:>9} {grand_tot:>7}")
if grand_tot > 0:
    print(f"\n  Accept rate: {100*grand_acc/grand_tot:.1f}%  |  Reject rate: {100*grand_rej/grand_tot:.1f}%")
