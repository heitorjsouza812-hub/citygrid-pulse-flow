from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from llm_decision.validate_artifact import validate_adapter_archive, validate_gguf


def test_validate_adapter_archive_reads_declared_base_model(tmp_path: Path) -> None:
    archive_path = tmp_path / "adapter.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("adapter/adapter_model.safetensors", b"synthetic-test-weights")
        archive.writestr(
            "adapter/adapter_config.json",
            json.dumps({"base_model_name_or_path": "mistralai/Ministral-3-3B-Instruct-2512"}),
        )
    report = validate_adapter_archive(archive_path)
    assert report["base_model"] == "mistralai/Ministral-3-3B-Instruct-2512"
    assert report["adapter_weight_bytes"] > 0


def test_validate_gguf_requires_magic_header(tmp_path: Path) -> None:
    good = tmp_path / "model.gguf"
    good.write_bytes(b"GGUF" + b"synthetic")
    assert validate_gguf(good)["magic"] == "GGUF"

    bad = tmp_path / "bad.gguf"
    bad.write_bytes(b"NOPE")
    with pytest.raises(ValueError, match="magic"):
        validate_gguf(bad)
