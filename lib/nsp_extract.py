import logging
from pathlib import Path

from .config import ToolkitConfig
from .keys import KeyManager
from .runner import run_command

logger = logging.getLogger("nsp_toolkit")


def extract_nca_from_nsp(
    nsp_path: Path,
    output_dir: Path,
    config: ToolkitConfig,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(config.hactool),
        "-t", "pfs0",
        "--pfs0dir", str(output_dir),
        str(nsp_path),
    ]
    logger.info("Extracting NCA files from NSP: %s", nsp_path.name)
    run_command(cmd)
    nca_files = sorted(output_dir.glob("*.nca"))
    logger.info("Extracted %d NCA file(s)", len(nca_files))
    return nca_files


def find_largest_nca(nca_dir: Path) -> Path:
    nca_files = list(nca_dir.glob("*.nca"))
    if not nca_files:
        raise FileNotFoundError(f"No NCA files found in {nca_dir}")
    largest = max(nca_files, key=lambda p: p.stat().st_size)
    size_mb = largest.stat().st_size / (1024 * 1024)
    logger.info("Largest NCA: %s (%.2f MB)", largest.name, size_mb)
    return largest


def find_tik_files(nca_dir: Path) -> list[Path]:
    tik_files = sorted(nca_dir.glob("*.tik"))
    logger.info("Found %d .tik file(s)", len(tik_files))
    return tik_files


def extract_titlekeys_from_dir(nca_dir: Path, key_mgr: KeyManager) -> dict[str, str]:
    tik_files = find_tik_files(nca_dir)
    titlekeys = {}
    for tik in tik_files:
        try:
            tk = KeyManager.extract_titlekey_from_tik(tik)
            rights_id = tik.stem
            titlekeys[rights_id] = tk
            logger.info("Title key from %s: %s", tik.name, tk)
        except Exception as e:
            logger.warning("Failed to extract titlekey from %s: %s", tik.name, e)
    return titlekeys
