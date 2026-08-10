"""Validate CityGrid training artifacts downloaded from Colab or Kaggle.

This checks artifact integrity before local conversion/import/benchmarking. It
never loads arbitrary pickle files or executes contents from the archive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
INCOMING_DIR = ROOT / "artifacts" / "incoming"
REQUIRED_ADAPTER_FILES = {"adapter/adapter_model.safetensors", "adapter/adapter_config.json"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_adapter_archive(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"adapter archive missing or empty: {path}")
    if not zipfile.is_zipfile(path):
        raise ValueError("adapter archive is not a valid ZIP")

    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"corrupt ZIP member: {bad_member}")
        members = {member.filename for member in archive.infolist() if not member.is_dir()}
        missing = REQUIRED_ADAPTER_FILES.difference(members)
        if missing:
            raise ValueError(f"required adapter files missing: {sorted(missing)}")
        raw_config = archive.read("adapter/adapter_config.json")
        config = json.loads(raw_config.decode("utf-8"))
        base_model = config.get("base_model_name_or_path")
        if not isinstance(base_model, str) or not base_model:
            raise ValueError("adapter_config.json lacks base_model_name_or_path")
        weights = archive.getinfo("adapter/adapter_model.safetensors")

    return {
        "type": "lora_adapter_zip",
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "base_model": base_model,
        "adapter_weight_bytes": weights.file_size,
        "required_files": sorted(REQUIRED_ADAPTER_FILES),
    }


def validate_gguf(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"GGUF missing or empty: {path}")
    with path.open("rb") as source:
        magic = source.read(4)
    if magic != b"GGUF":
        raise ValueError(f"invalid GGUF magic header: {magic!r}")
    return {
        "type": "gguf",
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "magic": magic.decode("ascii"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--gguf", type=Path)
    args = parser.parse_args()
    if not args.adapter and not args.gguf:
        parser.error("supply --adapter and/or --gguf")

    report: dict[str, Any] = {}
    if args.adapter:
        report["adapter"] = validate_adapter_archive(args.adapter)
    if args.gguf:
        report["gguf"] = validate_gguf(args.gguf)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
