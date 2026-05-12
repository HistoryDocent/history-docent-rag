from __future__ import annotations

from app.infrastructure.index.device import resolve_torch_device


def test_resolve_torch_device_keeps_explicit_device() -> None:
    assert resolve_torch_device("cpu") == "cpu"
    assert resolve_torch_device("cuda") == "cuda"


def test_resolve_torch_device_auto_is_portable() -> None:
    assert resolve_torch_device("auto") in {"cpu", "cuda"}
    assert resolve_torch_device("cuda_if_available") in {"cpu", "cuda"}
