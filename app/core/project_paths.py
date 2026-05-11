from __future__ import annotations

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def repository_root() -> Path:
    return _REPOSITORY_ROOT


def project_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return repository_root() / path


def repository_private_data_root() -> Path:
    return (repository_root() / "private_data").resolve()


def has_private_data_segment(path: Path) -> bool:
    candidate = project_path(path)
    resolved = candidate.resolve()
    return _contains_private_data_segment(candidate) or _contains_private_data_segment(
        resolved,
    )


def is_repository_private_artifact_path(path: Path) -> bool:
    private_root = repository_private_data_root()
    candidate = project_path(path)
    resolved = candidate.resolve()
    return is_relative_to_path(candidate.resolve(), private_root) or is_relative_to_path(
        resolved,
        private_root,
    )


def is_repository_private_write_path(path: Path) -> bool:
    private_root = repository_private_data_root()
    candidate = project_path(path)
    resolved = candidate.resolve()
    return is_relative_to_path(candidate.resolve(), private_root) and is_relative_to_path(
        resolved,
        private_root,
    )


def is_relative_to_path(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _contains_private_data_segment(path: Path) -> bool:
    return any(part.lower() == "private_data" for part in path.parts)
