"""Download and cache required local AI models for offline use."""

from __future__ import annotations

from pathlib import Path

from huggingface_hub import snapshot_download


ROOT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT_DIR / "models"

MODEL_SPECS = (
    {
        "repo_id": "facebook/musicgen-small",
        "target": MODELS_DIR / "musicgen-small",
        "label": "MusicGen Small",
        "size": "~300MB",
    },
    {
        "repo_id": "facebook/audiogen-medium",
        "target": MODELS_DIR / "audiogen-medium",
        "label": "AudioGen Medium",
        "size": "~1.5GB",
    },
    {
        "repo_id": "hexgrad/Kokoro-82M",
        "target": MODELS_DIR / "kokoro",
        "label": "Kokoro 82M",
        "size": "~330MB",
    },
)


def _is_model_present(path: Path) -> bool:
    if not path.is_dir():
        return False
    return any(path.iterdir())


def _download_model(repo_id: str, target: Path) -> None:
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(target),
        local_dir_use_symlinks=False,
        resume_download=True,
    )


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    failed_downloads: list[str] = []

    for spec in MODEL_SPECS:
        target = spec["target"]
        if _is_model_present(target):
            print(f"{spec['label']} already present at {target}. Skipping.")
            continue

        print(f"Downloading {spec['label']} ({spec['size']})...")
        target.mkdir(parents=True, exist_ok=True)
        try:
            _download_model(spec["repo_id"], target)
            print(f"Finished {spec['label']}.")
        except Exception as exc:
            failed_downloads.append(spec["label"])
            print(f"ERROR: Failed downloading {spec['label']}: {exc}")

    missing = [spec["label"] for spec in MODEL_SPECS if not _is_model_present(spec["target"])]
    if failed_downloads or missing:
        if failed_downloads:
            print("ERROR: Download failures occurred for:")
            for name in failed_downloads:
                print(f"  - {name}")
        print("ERROR: Some model folders are missing after download:")
        for name in missing:
            print(f"  - {name}")
        return 1

    print("All required models are present in models/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
