import logging
from pathlib import Path

from .config import ToolkitConfig
from .runner import run_command

logger = logging.getLogger("nsp_toolkit")


def decrypt_nca(
    nca_path: Path,
    config: ToolkitConfig,
    titlekey: str | None = None,
    basenca: Path | None = None,
    romfs_dir: Path | None = None,
    exefs_dir: Path | None = None,
) -> dict[str, Path | None]:
    cmd = [str(config.hactool), str(nca_path), "-k", str(config.prod_keys)]

    if titlekey:
        cmd.extend(["--titlekey", titlekey])
    if basenca:
        cmd.extend(["--basenca", str(basenca)])
    if romfs_dir:
        romfs_dir.mkdir(parents=True, exist_ok=True)
        cmd.extend(["--romfsdir", str(romfs_dir)])
    if exefs_dir:
        exefs_dir.mkdir(parents=True, exist_ok=True)
        cmd.extend(["--exefsdir", str(exefs_dir)])

    logger.info("Decrypting NCA: %s", nca_path.name)
    if titlekey:
        logger.debug("Using titlekey: %s", titlekey)
    if basenca:
        logger.debug("Using basenca: %s", basenca.name)

    result = run_command(cmd, check=False)

    if result.returncode != 0:
        logger.error("hactool failed for %s (exit %d)", nca_path.name, result.returncode)
        if result.stderr:
            for line in result.stderr.splitlines():
                if "corrupted" in line.lower():
                    logger.warning("hactool: %s", line.strip())

    output = {
        "romfs": romfs_dir if romfs_dir and romfs_dir.exists() else None,
        "exefs": exefs_dir if exefs_dir and exefs_dir.exists() else None,
    }

    if output["romfs"]:
        count = sum(1 for _ in output["romfs"].rglob("*") if _.is_file())
        logger.info("RomFS: %d file(s) extracted", count)
    if output["exefs"]:
        count = sum(1 for _ in output["exefs"].rglob("*") if _.is_file())
        logger.info("ExeFS: %d file(s) extracted", count)

    return output
