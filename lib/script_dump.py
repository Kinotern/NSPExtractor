import logging
import sys
from pathlib import Path

from .runner import run_command

logger = logging.getLogger("nsp_toolkit")


def find_nut_files(script_dir: Path) -> list[Path]:
    nut_files = sorted(script_dir.rglob("*.nut.m"))
    if not nut_files:
        logger.warning("No .nut.m files found in %s", script_dir)
    else:
        logger.info("Found %d .nut.m file(s)", len(nut_files))
    return nut_files


def dump_scripts(
    script_dir: Path,
    output_dir: Path,
    bytecode_dumper: Path,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    nut_files = find_nut_files(script_dir)
    if not nut_files:
        return 0

    success = 0
    failures = 0
    for idx, nut_file in enumerate(nut_files, 1):
        rel = nut_file.relative_to(script_dir)
        txt_out = output_dir / f"{rel}.txt"
        json_out = output_dir / f"{rel}.json"
        txt_out.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Script [%d/%d]: %s", idx, len(nut_files), rel)
        cmd = [
            sys.executable,
            str(bytecode_dumper),
            str(nut_file),
            "-o", str(txt_out),
            "--json", str(json_out),
        ]
        try:
            run_command(cmd)
            success += 1
        except Exception as e:
            failures += 1
            logger.error("Failed to dump %s: %s", nut_file.name, e)

    logger.info(
        "Script dump complete: %d success, %d failed", success, failures
    )
    return success
