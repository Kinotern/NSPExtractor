import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("nsp_toolkit")

ARCHIVE_CATEGORIES = {
    "image": "images",
    "script": "scripts",
    "sound": "audio",
    "voice": "voice",
    "scenario": "scenario",
    "motion": "motion",
    "font": "fonts",
    "config": "config",
}


def classify_romfs(romfs_dir: Path) -> dict[str, list[dict]]:
    categories: dict[str, list[dict]] = {}
    for info_file in sorted(romfs_dir.rglob("*_info.psb.m")):
        stem = info_file.name.replace("_info.psb.m", "")
        body_file = info_file.parent / f"{stem}_body.bin"
        category = "other"
        for prefix, cat in ARCHIVE_CATEGORIES.items():
            if stem.startswith(prefix):
                category = cat
                break
        entry = {
            "name": stem,
            "info_file": str(info_file.relative_to(romfs_dir)),
            "body_file": str(body_file.relative_to(romfs_dir)) if body_file.exists() else None,
            "body_size": body_file.stat().st_size if body_file.exists() else 0,
            "category": category,
        }
        categories.setdefault(category, []).append(entry)
    return categories


def count_files(directory: Path) -> dict[str, int]:
    if not directory or not directory.exists():
        return {"files": 0, "dirs": 0}
    files = sum(1 for p in directory.rglob("*") if p.is_file())
    dirs = sum(1 for p in directory.rglob("*") if p.is_dir())
    return {"files": files, "dirs": dirs}


def generate_metadata(
    nsp_name: str,
    output_dir: Path,
    nca_dir: Path | None = None,
    exefs_dir: Path | None = None,
    romfs_dir: Path | None = None,
    images_dir: Path | None = None,
    scripts_dir: Path | None = None,
    titlekeys: dict[str, str] | None = None,
    errors: list[str] | None = None,
) -> Path:
    meta = {
        "nsp_name": nsp_name,
        "timestamp": datetime.now().isoformat(),
        "toolkit_version": "1.0.0",
        "titlekeys": titlekeys or {},
        "errors": errors or [],
        "structure": {},
    }

    if nca_dir and nca_dir.exists():
        nca_files = [
            {"name": f.name, "size": f.stat().st_size}
            for f in sorted(nca_dir.glob("*.nca"))
        ]
        meta["structure"]["nca"] = {"path": str(nca_dir.relative_to(output_dir)), "files": nca_files}

    if exefs_dir and exefs_dir.exists():
        exefs_files = [
            {"name": f.name, "size": f.stat().st_size}
            for f in sorted(exefs_dir.rglob("*"))
            if f.is_file()
        ]
        stats = count_files(exefs_dir)
        meta["structure"]["exefs"] = {
            "path": str(exefs_dir.relative_to(output_dir)),
            "file_count": stats["files"],
            "files": exefs_files,
        }

    if romfs_dir and romfs_dir.exists():
        stats = count_files(romfs_dir)
        categories = classify_romfs(romfs_dir)
        meta["structure"]["romfs"] = {
            "path": str(romfs_dir.relative_to(output_dir)),
            "file_count": stats["files"],
            "archives": categories,
        }

    if images_dir and images_dir.exists():
        stats = count_files(images_dir)
        meta["structure"]["images"] = {
            "path": str(images_dir.relative_to(output_dir)),
            "file_count": stats["files"],
        }

    if scripts_dir and scripts_dir.exists():
        stats = count_files(scripts_dir)
        meta["structure"]["scripts"] = {
            "path": str(scripts_dir.relative_to(output_dir)),
            "file_count": stats["files"],
        }

    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Metadata written to %s", meta_path)
    return meta_path
