from __future__ import annotations


def resolve_torch_device(device: str) -> str:
    normalized = device.strip().lower()
    if normalized not in {"auto", "cuda_if_available"}:
        return device
    try:
        import torch
    except ImportError:
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"
