import logging
from pathlib import Path

from .config import ToolkitConfig
from .runner import run_command

logger = logging.getLogger("nsp_toolkit")


def extract_images(
    input_dir: Path,
    output_dir: Path,
    config: ToolkitConfig,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    psb_files = sorted(input_dir.rglob("*.psb.m"))
    if not psb_files:
        psb_files = sorted(input_dir.rglob("*.psb"))
    if not psb_files:
        logger.warning("No .psb/.psb.m files found in %s", input_dir)
        return 0

    success = 0
    failures = 0
    for idx, psb_file in enumerate(psb_files, 1):
        logger.info(
            "Image [%d/%d]: %s", idx, len(psb_files), psb_file.name
        )
        cmd = [
            str(config.psb_decompile),
            "image",
            "-o", str(output_dir),
            str(psb_file),
        ]
        try:
            run_command(cmd)
            success += 1
        except Exception as e:
            failures += 1
            logger.error("Failed to extract image %s: %s", psb_file.name, e)

    logger.info(
        "Image extraction complete: %d success, %d failed", success, failures
    )
    return success
