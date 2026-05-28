import json
from pathlib import Path


SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".m4v"}


def splitext_name(filename: str) -> tuple[str, str]:
    p = Path(filename)
    return p.stem, p.suffix.lower()


def generate_output_filename(source_name: str, suffix: str) -> str:
    stem, _ext = splitext_name(source_name)
    return f"{stem}-{suffix}.mp4"


def generate_thumbnail_filename(source_name: str, suffix: str) -> str:
    stem, _ext = splitext_name(source_name)
    return f"{stem}-{suffix}-thumbnail.jpg"


def read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
