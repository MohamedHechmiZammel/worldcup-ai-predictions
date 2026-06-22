"""
Download training data for the World Cup AI prediction model.

Sources:
  1. Kaggle "International football results 1872-2024"
     (martj42/international-football-results-from-1872-to-2017)
  2. StatsBomb Open Data — matches JSON files (World Cup competition_id=43
     plus other major tournaments)
"""

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import httpx as _http_lib
    _HTTP_LIB = "httpx"
except ImportError:
    try:
        import requests as _http_lib  # type: ignore[no-redef]
        _HTTP_LIB = "requests"
    except ImportError:
        _http_lib = None  # type: ignore[assignment]
        _HTTP_LIB = None

DATA_DIR = Path(__file__).parent / "data" / "raw"

# ---------------------------------------------------------------------------
# Kaggle
# ---------------------------------------------------------------------------

KAGGLE_DATASET = "martj42/international-football-results-from-1872-to-2017"
KAGGLE_FALLBACK_URL = (
    "https://raw.githubusercontent.com/martj42/international-football-results"
    "/master/results.csv"
)
RESULTS_CSV = DATA_DIR / "results.csv"


def _http_get(url: str) -> bytes:
    """Fetch *url* and return its raw bytes, using httpx or requests."""
    if _HTTP_LIB is None:
        raise RuntimeError(
            "No HTTP library found. Install httpx or requests:\n"
            "  pip install httpx"
        )
    if _HTTP_LIB == "httpx":
        with _http_lib.Client(follow_redirects=True, timeout=60) as client:  # type: ignore[attr-defined]
            response = client.get(url)
            response.raise_for_status()
            return response.content
    else:
        response = _http_lib.get(url, timeout=60)  # type: ignore[attr-defined]
        response.raise_for_status()
        return response.content


def _kaggle_credentials_available() -> bool:
    """Return True if the kaggle CLI is installed and credentials exist."""
    try:
        result = subprocess.run(
            ["kaggle", "datasets", "list", "--max-size", "1"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def download_kaggle() -> None:
    """Download the international football results CSV via the kaggle CLI.

    Falls back to a direct HTTP download from GitHub when the kaggle CLI is
    not installed or credentials are not configured.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if RESULTS_CSV.exists():
        print(f"[kaggle] results.csv already present at {RESULTS_CSV} — skipping.")
        return

    if _kaggle_credentials_available():
        print("[kaggle] Downloading via kaggle CLI …")
        cmd = [
            "kaggle",
            "datasets",
            "download",
            "-d",
            KAGGLE_DATASET,
            "-p",
            str(DATA_DIR),
            "--unzip",
        ]
        result = subprocess.run(cmd, text=True)
        if result.returncode == 0 and RESULTS_CSV.exists():
            print(f"[kaggle] Saved to {RESULTS_CSV}")
            return
        print("[kaggle] CLI download failed; falling back to HTTP.")

    else:
        print(
            "[kaggle] kaggle CLI not found or credentials not configured.\n"
            "  To use the CLI:\n"
            "    1. pip install kaggle\n"
            "    2. Create an API token at https://www.kaggle.com/settings\n"
            "    3. Place kaggle.json in ~/.kaggle/ (chmod 600)\n"
            "  Falling back to HTTP download from GitHub …"
        )

    # HTTP fallback
    print(f"[kaggle] Fetching {KAGGLE_FALLBACK_URL} …")
    data = _http_get(KAGGLE_FALLBACK_URL)
    RESULTS_CSV.write_bytes(data)
    print(f"[kaggle] Saved {len(data):,} bytes to {RESULTS_CSV}")


# ---------------------------------------------------------------------------
# StatsBomb Open Data
# ---------------------------------------------------------------------------

STATSBOMB_BASE_URL = (
    "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
)
STATSBOMB_DIR = DATA_DIR / "statsbomb"

# competition_id -> human-readable name (subset of major tournaments)
COMPETITIONS_OF_INTEREST = {
    43: "FIFA World Cup",
    2: "UEFA Champions League",
    11: "La Liga",
    37: "English Women's Super League",
    49: "NWSL",
    72: "Women's World Cup",
}


def _statsbomb_competitions() -> list[dict]:
    """Fetch the StatsBomb competitions index."""
    url = f"{STATSBOMB_BASE_URL}/competitions.json"
    print(f"[statsbomb] Fetching competitions index from {url} …")
    import json

    raw = _http_get(url)
    return json.loads(raw)


def _download_file(url: str, dest: Path) -> None:
    """Download *url* to *dest*, creating parent directories as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return  # already downloaded
    data = _http_get(url)
    dest.write_bytes(data)


def download_statsbomb() -> None:
    """Download StatsBomb open-data match files for selected competitions.

    Files are saved under ``backend/ml/data/raw/statsbomb/matches/``.
    """
    import json

    STATSBOMB_DIR.mkdir(parents=True, exist_ok=True)

    competitions = _statsbomb_competitions()

    # Filter to the competitions we care about
    selected = [
        c
        for c in competitions
        if c["competition_id"] in COMPETITIONS_OF_INTEREST
    ]

    if not selected:
        print("[statsbomb] No matching competitions found in the index.")
        return

    print(
        f"[statsbomb] Found {len(selected)} competition/season combinations "
        f"across {len({c['competition_id'] for c in selected})} competitions."
    )

    for entry in selected:
        comp_id = entry["competition_id"]
        season_id = entry["season_id"]
        comp_name = entry.get("competition_name", f"comp_{comp_id}")
        season_name = entry.get("season_name", f"season_{season_id}")

        matches_url = (
            f"{STATSBOMB_BASE_URL}/matches/{comp_id}/{season_id}.json"
        )
        dest = STATSBOMB_DIR / "matches" / f"{comp_id}" / f"{season_id}.json"

        print(f"[statsbomb]   {comp_name} / {season_name} → {dest.relative_to(DATA_DIR.parent.parent)}")
        try:
            _download_file(matches_url, dest)
        except Exception as exc:  # noqa: BLE001
            print(f"[statsbomb]   WARNING: could not download {matches_url}: {exc}")

    # Report summary
    saved = list((STATSBOMB_DIR / "matches").rglob("*.json"))
    print(f"[statsbomb] Done. {len(saved)} match files saved under {STATSBOMB_DIR}.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download training data for the World Cup AI prediction model."
    )
    parser.add_argument(
        "--source",
        choices=["all", "kaggle", "statsbomb"],
        default="all",
        help="Which data source(s) to download (default: all).",
    )
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.source in ("all", "kaggle"):
        try:
            download_kaggle()
        except Exception as exc:  # noqa: BLE001
            print(f"[kaggle] ERROR: {exc}", file=sys.stderr)

    if args.source in ("all", "statsbomb"):
        if _HTTP_LIB is None:
            print(
                "[statsbomb] ERROR: no HTTP library available.\n"
                "  Install one of: httpx, requests",
                file=sys.stderr,
            )
        else:
            try:
                download_statsbomb()
            except Exception as exc:  # noqa: BLE001
                print(f"[statsbomb] ERROR: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
