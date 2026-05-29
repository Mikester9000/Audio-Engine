"""Download and cache required local AI models for offline use.

Usage
-----
  python tools/download_models.py                    # download all missing models
  python tools/download_models.py --model small      # download MusicGen Small only
  python tools/download_models.py --model medium     # download MusicGen Medium only
  python tools/download_models.py --skip             # skip download, show manual placement instructions
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT_DIR / "models"

MODEL_SPECS = (
    {
        "repo_id": "facebook/musicgen-small",
        "target": MODELS_DIR / "musicgen-small",
        "label": "MusicGen Small",
        "key": "small",
        "size": "~300MB",
    },
    {
        "repo_id": "facebook/musicgen-medium",
        "target": MODELS_DIR / "musicgen-medium",
        "label": "MusicGen Medium",
        "key": "medium",
        "size": "~1.5GB",
    },
)

_MANUAL_INSTRUCTIONS = """\
Manual model placement instructions
------------------------------------
If the download stalls or fails, you can download the models yourself:

  MusicGen Small  (~300 MB, faster/lighter):
    1. Visit: https://huggingface.co/facebook/musicgen-small/tree/main
    2. Download all files in that repository.
    3. Place them in: {models_dir}\\musicgen-small\\

  MusicGen Medium (~1.5 GB, higher quality):
    1. Visit: https://huggingface.co/facebook/musicgen-medium/tree/main
    2. Download all files in that repository.
    3. Place them in: {models_dir}\\musicgen-medium\\

Setting a Hugging Face token (recommended for faster authenticated downloads):
  Windows:  set HF_TOKEN=your_token_here
  Linux:    export HF_TOKEN=your_token_here

You can get a free token at: https://huggingface.co/settings/tokens

After placing the model files manually, re-run:
  python tools\\download_models.py
to verify the models are recognised.
"""


def _is_model_present(path: Path) -> bool:
    try:
        from audio_engine.ai.backends._paths import has_complete_model_snapshot
    except ImportError:
        return path.is_dir() and any(path.iterdir())
    return has_complete_model_snapshot(path)


def _download_model(repo_id: str, target: Path) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub is not installed. Install AI dependencies first:\n"
            "  pip install -e \".[musicgen]\""
        ) from exc
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(target),
    )


def _print_manual_instructions() -> None:
    print(_MANUAL_INSTRUCTIONS.format(models_dir=MODELS_DIR))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download Audio Engine AI models.")
    parser.add_argument(
        "--skip",
        action="store_true",
        help="Skip download and print manual placement instructions instead.",
    )
    parser.add_argument(
        "--model",
        choices=["small", "medium", "all"],
        default="all",
        help=(
            "Which MusicGen model to download: 'small' (~300 MB, faster), "
            "'medium' (~1.5 GB, higher quality), or 'all' (default)."
        ),
    )
    args = parser.parse_args(argv)

    if args.skip:
        print("Download skipped. Printing manual placement instructions...\n")
        _print_manual_instructions()
        return 0

    selected_key = args.model
    specs_to_download = [
        spec for spec in MODEL_SPECS
        if selected_key == "all" or spec["key"] == selected_key
    ]

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    failed_downloads: list[str] = []

    for spec in specs_to_download:
        target = spec["target"]
        if _is_model_present(target):
            print(f"{spec['label']} already present at {target}. Skipping.")
            continue

        print(f"Downloading {spec['label']} ({spec['size']})...")
        print(f"  Repository: {spec['repo_id']}")
        print(f"  Destination: {target}")
        if not sys.stdout.isatty():
            print("  (progress output may be buffered in non-interactive terminals)")
        target.mkdir(parents=True, exist_ok=True)
        try:
            _download_model(spec["repo_id"], target)
            print(f"Finished {spec['label']}.")
        except Exception as exc:
            failed_downloads.append(spec["label"])
            detail = str(exc).strip() or exc.__class__.__name__
            print(f"ERROR: Failed downloading {spec['label']}: {detail}")

    failed_set = set(failed_downloads)
    missing = [
        spec["label"]
        for spec in specs_to_download
        if spec["label"] not in failed_set and not _is_model_present(spec["target"])
    ]
    if failed_downloads or missing:
        if failed_downloads:
            print("ERROR: Download failures occurred for:")
            for name in failed_downloads:
                print(f"  - {name}")
        if missing:
            print("ERROR: Some model folders are missing after download:")
            for name in missing:
                print(f"  - {name}")
        print()
        _print_manual_instructions()
        return 1

    print("All requested models are present in models/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT_DIR / "models"

MODEL_SPECS = (
    {
        "repo_id": "facebook/musicgen-medium",
        "target": MODELS_DIR / "musicgen-medium",
        "label": "MusicGen Medium",
        "size": "~1.5GB",
    },
)

_MANUAL_INSTRUCTIONS = """\
Manual model placement instructions
------------------------------------
If the download stalls or fails, you can download the model yourself:

  1. Visit: https://huggingface.co/facebook/musicgen-medium/tree/main
  2. Download all files in that repository.
  3. Place them in: {models_dir}\\musicgen-medium\\

Setting a Hugging Face token (recommended for faster authenticated downloads):
  Windows:  set HF_TOKEN=your_token_here
  Linux:    export HF_TOKEN=your_token_here

You can get a free token at: https://huggingface.co/settings/tokens

After placing the model files manually, re-run:
  python tools\\download_models.py
to verify the model is recognised.
"""


def _is_model_present(path: Path) -> bool:
    try:
        from audio_engine.ai.backends._paths import has_complete_model_snapshot
    except ImportError:
        return path.is_dir() and any(path.iterdir())
    return has_complete_model_snapshot(path)


def _download_model(repo_id: str, target: Path) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub is not installed. Install AI dependencies first:\n"
            "  pip install -e \".[musicgen]\""
        ) from exc
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(target),
    )


def _print_manual_instructions() -> None:
    print(_MANUAL_INSTRUCTIONS.format(models_dir=MODELS_DIR))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download Audio Engine AI models.")
    parser.add_argument(
        "--skip",
        action="store_true",
        help="Skip download and print manual placement instructions instead.",
    )
    args = parser.parse_args(argv)

    if args.skip:
        print("Download skipped. Printing manual placement instructions...\n")
        _print_manual_instructions()
        return 0

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    failed_downloads: list[str] = []

    for spec in MODEL_SPECS:
        target = spec["target"]
        if _is_model_present(target):
            print(f"{spec['label']} already present at {target}. Skipping.")
            continue

        print(f"Downloading {spec['label']} ({spec['size']})...")
        print(f"  Repository: {spec['repo_id']}")
        print(f"  Destination: {target}")
        if not sys.stdout.isatty():
            print("  (progress output may be buffered in non-interactive terminals)")
        target.mkdir(parents=True, exist_ok=True)
        try:
            _download_model(spec["repo_id"], target)
            print(f"Finished {spec['label']}.")
        except Exception as exc:
            failed_downloads.append(spec["label"])
            detail = str(exc).strip() or exc.__class__.__name__
            print(f"ERROR: Failed downloading {spec['label']}: {detail}")

    failed_set = set(failed_downloads)
    missing = [
        spec["label"]
        for spec in MODEL_SPECS
        if spec["label"] not in failed_set and not _is_model_present(spec["target"])
    ]
    if failed_downloads or missing:
        if failed_downloads:
            print("ERROR: Download failures occurred for:")
            for name in failed_downloads:
                print(f"  - {name}")
        if missing:
            print("ERROR: Some model folders are missing after download:")
            for name in missing:
                print(f"  - {name}")
        print()
        _print_manual_instructions()
        return 1

    print("All required models are present in models/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
