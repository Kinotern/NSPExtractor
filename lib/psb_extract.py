import logging
from pathlib import Path

from .config import ToolkitConfig
from .runner import run_command

logger = logging.getLogger("nsp_toolkit")


def find_psb_archives(romfs_dir: Path) -> list[tuple[str, Path, Path]]:
    archives = []
    info_files = sorted(romfs_dir.rglob("*_info.psb.m"))
    for info_file in info_files:
        stem = info_file.name.replace("_info.psb.m", "")
        body_file = info_file.parent / f"{stem}_body.bin"
        if body_file.exists():
            archives.append((stem, info_file, body_file))
            logger.debug("Found archive pair: %s", stem)
        else:
            logger.warning("Missing body for: %s (expected %s)", info_file.name, body_file.name)
    logger.info("Found %d PSB archive pair(s)", len(archives))
    return archives


def extract_psb_archive(
    info_file: Path,
    output_dir: Path,
    config: ToolkitConfig,
    key: str | None = None,
    key_length: str | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(config.psb_decompile),
        "info-psb",
        "-k", key or config.mdf_key,
        "-l", key_length or config.mdf_key_length,
        "-o", str(output_dir),
        str(info_file),
    ]
    logger.info("Extracting PSB archive: %s -> %s", info_file.name, output_dir.name)
    run_command(cmd)
    file_count = sum(1 for _ in output_dir.rglob("*") if _.is_file())
    logger.info("Extracted %d file(s) from %s", file_count, info_file.name)
    return output_dir
