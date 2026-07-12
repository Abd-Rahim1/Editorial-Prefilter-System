"""
prepare_iclr.py
---------------
Senior Data Engineer script for TFG Layer-3 dataset preparation.

Workflow:
  1. Scan all JSON review files in the raw PeerRead iclr_2017 split folders
     (train / dev / test) and extract paper_id + accepted label.
  2. Write a master CSV  →  data/processed/iclr_2017_metadata.csv
  3. Apply a NEW stratified split (75 % train / 10 % val / 15 % test)
     across the FULL corpus, ignoring the original PeerRead split.
  4. Create the target directory tree inside data/processed/iclr_2017/.
  5. COPY the corresponding PDF from the raw dataset into the right bucket.
  6. Write a placeholder  <paper_id>_features.json  next to each PDF.
  7. Print a per-split / per-class count report for the thesis.

Usage (from project root):
    python src/dataset/prepare_iclr.py [--dry-run]

Flags:
    --dry-run   Print what would happen without touching the filesystem.
"""

import argparse
import json
import logging
import random
import shutil
import sys
from pathlib import Path

# ─────────────────────────── configuration ────────────────────────────────────

# Resolve project root relative to this file's location
SCRIPT_DIR = Path(__file__).resolve().parent          # src/dataset/
SRC_DIR    = SCRIPT_DIR.parent                        # src/
PROJECT_ROOT = SRC_DIR.parent                         # project root

# Raw dataset root (one level above the project root, then into Dataset/)
RAW_ROOT = PROJECT_ROOT.parent / "Dataset" / "PeerRead" / "data" / "iclr_2017"

# Processed output locations
PROCESSED_DIR  = PROJECT_ROOT / "data" / "processed"
MASTER_CSV     = PROCESSED_DIR / "iclr_2017_metadata.csv"
ORGANIZED_ROOT = PROCESSED_DIR / "iclr_2017"

# Split ratios (must sum to 1.0)
TRAIN_RATIO = 0.75
VAL_RATIO   = 0.10
TEST_RATIO  = 0.15

# Random seed for reproducibility
RANDOM_SEED = 42

# Original PeerRead split folder names
PEERREAD_SPLITS = ("train", "dev", "test")

# ──────────────────────────── logging setup ────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ──────────────────────────── helper functions ─────────────────────────────────

def extract_labels(raw_root: Path) -> list[dict]:
    """
    Walk every split's reviews/ folder and extract:
        paper_id, label (1/0), original_split, pdf_source_path
    Returns a list of record dicts, sorted by paper_id.
    """
    records: list[dict] = []
    seen_ids: set[str] = set()

    for split in PEERREAD_SPLITS:
        reviews_dir = raw_root / split / "reviews"
        pdfs_dir    = raw_root / split / "pdfs"

        if not reviews_dir.is_dir():
            log.warning("Reviews directory not found: %s — skipping.", reviews_dir)
            continue

        json_files = sorted(reviews_dir.glob("*.json"))
        log.info("Split %-6s → found %d JSON files.", split, len(json_files))

        for jf in json_files:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                log.error("Cannot read %s: %s", jf, exc)
                continue

            paper_id = str(data.get("id", jf.stem))

            if paper_id in seen_ids:
                log.warning("Duplicate paper_id %s in split=%s — skipping.", paper_id, split)
                continue
            seen_ids.add(paper_id)

            accepted  = bool(data.get("accepted", False))
            label     = 1 if accepted else 0

            pdf_path = pdfs_dir / f"{paper_id}.pdf"
            if not pdf_path.is_file():
                log.warning("PDF missing for paper_id=%s (expected %s).", paper_id, pdf_path)
                pdf_path = None  # will be noted but not copied

            records.append({
                "paper_id":       paper_id,
                "label":          label,
                "original_split": split,
                "pdf_src":        pdf_path,   # Path | None  (not written to CSV)
            })

    records.sort(key=lambda r: r["paper_id"])
    log.info("Total papers extracted: %d  (accepted=%d, rejected=%d)",
             len(records),
             sum(r["label"] for r in records),
             sum(1 for r in records if r["label"] == 0))
    return records


def write_master_csv(records: list[dict], csv_path: Path, dry_run: bool) -> None:
    """Write the master metadata CSV (paper_id, label, original_split)."""
    if dry_run:
        log.info("[DRY-RUN] Would write master CSV → %s  (%d rows)", csv_path, len(records))
        return
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8") as fh:
        fh.write("paper_id,label,original_split\n")
        for r in records:
            fh.write(f"{r['paper_id']},{r['label']},{r['original_split']}\n")
    log.info("Master CSV written → %s  (%d rows)", csv_path, len(records))


def stratified_split(records: list[dict],
                     train_ratio: float,
                     val_ratio:   float,
                     seed:        int) -> dict[str, list[dict]]:
    """
    Perform a deterministic stratified 3-way split preserving class balance.
    Returns {"train": [...], "val": [...], "test": [...]}.
    """
    rng = random.Random(seed)

    accepted = [r for r in records if r["label"] == 1]
    rejected = [r for r in records if r["label"] == 0]

    def split_class(items: list[dict]) -> tuple[list, list, list]:
        items = items[:]
        rng.shuffle(items)
        n     = len(items)
        n_tr  = round(n * train_ratio)
        n_val = round(n * val_ratio)
        return items[:n_tr], items[n_tr:n_tr + n_val], items[n_tr + n_val:]

    tr_acc, val_acc, te_acc = split_class(accepted)
    tr_rej, val_rej, te_rej = split_class(rejected)

    return {
        "train": tr_acc  + tr_rej,
        "val":   val_acc + val_rej,
        "test":  te_acc  + te_rej,
    }


def build_directory_tree(organized_root: Path, dry_run: bool) -> None:
    """Create the split × class directory structure."""
    for split in ("train", "val", "test"):
        for cls in ("accepted", "rejected"):
            target = organized_root / split / cls
            if dry_run:
                log.info("[DRY-RUN] Would create dir: %s", target)
            else:
                target.mkdir(parents=True, exist_ok=True)


def deploy_papers(split_map: dict[str, list[dict]],
                  organized_root: Path,
                  dry_run: bool) -> dict:
    """
    Copy PDFs and write placeholder _features.json files.
    Returns a nested count dict for the report.
    """
    counts: dict[str, dict[str, int]] = {
        s: {"accepted": 0, "rejected": 0, "missing_pdf": 0}
        for s in ("train", "val", "test")
    }

    for split, records in split_map.items():
        for rec in records:
            cls     = "accepted" if rec["label"] == 1 else "rejected"
            dest_dir = organized_root / split / cls
            pid      = rec["paper_id"]
            pdf_src  = rec["pdf_src"]

            # ── Copy PDF ──────────────────────────────────────────────────────
            if pdf_src is None:
                counts[split]["missing_pdf"] += 1
                log.warning("No PDF to copy for paper_id=%s in split=%s.", pid, split)
                continue

            pdf_dest = dest_dir / f"{pid}.pdf"
            if dry_run:
                log.debug("[DRY-RUN] Would copy %s → %s", pdf_src.name, pdf_dest)
            else:
                shutil.copy2(pdf_src, pdf_dest)

            # ── Placeholder features JSON ─────────────────────────────────────
            placeholder = {
                "paper_id":   pid,
                "label":      rec["label"],
                "split":      split,
                "features":   {},
                "_note":      "Placeholder — populate with Layer-3 features.",
            }
            json_dest = dest_dir / f"{pid}_features.json"
            if dry_run:
                log.debug("[DRY-RUN] Would write %s", json_dest)
            else:
                json_dest.write_text(
                    json.dumps(placeholder, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

            counts[split][cls] += 1

    return counts


def print_report(counts: dict, split_map: dict) -> None:
    """Print a formatted thesis-ready summary table."""
    separator = "-" * 58
    print(f"\n{separator}")
    print("  ICLR 2017  ─  Dataset Preparation Report")
    print(separator)
    print(f"  {'Split':<10} {'Accepted':>10} {'Rejected':>10} {'Missing':>9} {'Total':>8}")
    print(separator)

    grand_acc = grand_rej = grand_mis = 0
    for split in ("train", "val", "test"):
        c   = counts[split]
        acc = c["accepted"]
        rej = c["rejected"]
        mis = c["missing_pdf"]
        tot = acc + rej
        grand_acc += acc
        grand_rej += rej
        grand_mis += mis
        print(f"  {split.capitalize():<10} {acc:>10} {rej:>10} {mis:>9} {tot:>8}")

    print(separator)
    grand_tot = grand_acc + grand_rej
    print(f"  {'TOTAL':<10} {grand_acc:>10} {grand_rej:>10} {grand_mis:>9} {grand_tot:>8}")
    print(separator)

    # Per-split ratios
    total_papers = sum(len(v) for v in split_map.values())
    print("\n  Effective split ratios (papers with PDF):")
    for split in ("train", "val", "test"):
        c   = counts[split]
        tot = c["accepted"] + c["rejected"]
        pct = (tot / total_papers * 100) if total_papers else 0
        print(f"    {split.capitalize():<6}: {tot:>4} papers  ({pct:.1f} %)")
    print()


# ─────────────────────────────── main ─────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview all operations without writing any files.",
    )
    args = parser.parse_args(argv)
    dry_run: bool = args.dry_run

    if dry_run:
        log.info("=== DRY-RUN MODE — no files will be written ===")

    # ── Step 1: extract labels ────────────────────────────────────────────────
    log.info("Step 1 │ Extracting labels from raw PeerRead JSON files …")
    records = extract_labels(RAW_ROOT)
    if not records:
        log.error("No records found. Check RAW_ROOT path: %s", RAW_ROOT)
        return 1

    # ── Step 2: write master CSV ──────────────────────────────────────────────
    log.info("Step 2 │ Writing master CSV …")
    write_master_csv(records, MASTER_CSV, dry_run)

    # ── Step 3: stratified split ──────────────────────────────────────────────
    log.info("Step 3 │ Computing stratified 75/10/15 split (seed=%d) …", RANDOM_SEED)
    split_map = stratified_split(records, TRAIN_RATIO, VAL_RATIO, RANDOM_SEED)
    for s, recs in split_map.items():
        n_acc = sum(r["label"] for r in recs)
        n_rej = len(recs) - n_acc
        log.info("  %-6s → %d papers  (accepted=%d, rejected=%d)", s, len(recs), n_acc, n_rej)

    # ── Step 4: create directory tree ─────────────────────────────────────────
    log.info("Step 4 │ Building directory tree under %s …", ORGANIZED_ROOT)
    build_directory_tree(ORGANIZED_ROOT, dry_run)

    # ── Step 5 + 6: copy PDFs + write feature placeholders ───────────────────
    log.info("Step 5+6 │ Copying PDFs and writing placeholder JSON files …")
    counts = deploy_papers(split_map, ORGANIZED_ROOT, dry_run)

    # ── Step 7: report ────────────────────────────────────────────────────────
    print_report(counts, split_map)

    if dry_run:
        log.info("=== DRY-RUN complete — rerun without --dry-run to apply. ===")
    else:
        log.info("All done. Output root: %s", ORGANIZED_ROOT)

    return 0


if __name__ == "__main__":
    sys.exit(main())
