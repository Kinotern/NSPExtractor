import argparse
import logging
import re
import shutil
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.config import ToolkitConfig
from lib.logger import setup_logging
from lib.keys import KeyManager
from lib.nsp_extract import (
    extract_nca_from_nsp,
    extract_titlekeys_from_dir,
    find_largest_nca,
)
from lib.nca_decrypt import decrypt_nca
from lib.psb_extract import extract_psb_archive, find_psb_archives
from lib.image_extract import extract_images
from lib.script_dump import dump_scripts
from lib.metadata import generate_metadata

logger = logging.getLogger("nsp_toolkit")


def sanitize_nsp_name(name: str) -> str:
    stem = Path(name).stem
    return re.sub(r'[<>:"/\\|?*]', "_", stem).strip()


def _ascii_safe_path(path: Path) -> Path:
    try:
        str(path.resolve()).encode("ascii")
        return path
    except UnicodeEncodeError:
        import tempfile
        return Path(tempfile.gettempdir()) / "nsp_work"


def select_folder_gui() -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="Select folder containing NSP files")
        root.destroy()
        return Path(folder) if folder else None
    except Exception:
        return None


def select_files_gui() -> list[Path] | None:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        files = filedialog.askopenfilenames(
            title="Select NSP files",
            filetypes=[("NSP files", "*.nsp"), ("All files", "*.*")],
        )
        root.destroy()
        return [Path(f) for f in files] if files else None
    except Exception:
        return None


def find_nsp_files(directory: Path) -> list[Path]:
    nsp_files = sorted(directory.glob("*.nsp"))
    if not nsp_files:
        nsp_files = sorted(directory.rglob("*.nsp"))
    return nsp_files


def process_single_nsp(
    nsp_path: Path,
    config: ToolkitConfig,
    key_mgr: KeyManager,
    stages: list[str],
) -> Path:
    nsp_name = sanitize_nsp_name(nsp_path.name)
    output_dir = config.out_dir / nsp_name
    output_dir.mkdir(parents=True, exist_ok=True)

    work_root = _ascii_safe_path(config.work_dir) / nsp_name
    work_root.mkdir(parents=True, exist_ok=True)

    keys_work = work_root / "_keys"
    keys_work.mkdir(parents=True, exist_ok=True)
    saved_prod_keys = config.prod_keys
    saved_title_keys = config.title_keys
    if config.prod_keys.exists():
        work_prod = keys_work / "prod.keys"
        shutil.copy2(config.prod_keys, work_prod)
        config._prod_keys = work_prod
    if config.title_keys and config.title_keys.exists():
        work_title = keys_work / "title.keys"
        shutil.copy2(config.title_keys, work_title)
        config._title_keys = work_title

    nca_dir = work_root / "nca"
    exefs_dir = work_root / "exefs"
    romfs_dir = work_root / "romfs"
    archives_dir = work_root / "archives"
    images_dir = work_root / "images"
    scripts_dir = work_root / "scripts"

    final_nca_dir = output_dir / "nca"
    final_exefs_dir = output_dir / "exefs"
    final_romfs_dir = output_dir / "romfs"
    final_images_dir = output_dir / "images"
    final_scripts_dir = output_dir / "scripts"

    for src, dst in [
        (final_nca_dir, nca_dir),
        (final_exefs_dir, exefs_dir),
        (final_romfs_dir, romfs_dir),
        (final_images_dir, images_dir),
        (final_scripts_dir, scripts_dir),
    ]:
        if src.exists() and not dst.exists():
            logger.info("Restoring %s from previous run...", src.name)
            shutil.copytree(src, dst)

    titlekeys: dict[str, str] = {}
    errors: list[str] = []

    prev_meta = output_dir / "metadata.json"
    if prev_meta.exists() and "nca" not in stages:
        try:
            import json
            data = json.loads(prev_meta.read_text(encoding="utf-8"))
            titlekeys = data.get("titlekeys", {})
            if titlekeys:
                logger.info("Restored %d titlekey(s) from previous run", len(titlekeys))
        except Exception:
            pass

    logger.info("=" * 60)
    logger.info("Processing: %s", nsp_path.name)
    logger.info("Output: %s", output_dir)
    logger.info("Work dir: %s", work_root)
    logger.info("=" * 60)

    if "nca" in stages:
        logger.info("[Stage 1/5] Extracting NCA files from NSP...")
        try:
            extract_nca_from_nsp(nsp_path, nca_dir, config)
            titlekeys = extract_titlekeys_from_dir(nca_dir, key_mgr)
        except Exception as e:
            errors.append(f"NCA extraction failed: {e}")
            logger.exception("NCA extraction failed")

    if "decrypt" in stages:
        logger.info("[Stage 2/5] Decrypting NCA -> ExeFS + RomFS...")
        try:
            largest_nca = find_largest_nca(nca_dir)
            tk_hex = None
            if titlekeys:
                tk_hex = next(iter(titlekeys.values()), None)
            decrypt_nca(
                largest_nca,
                config,
                titlekey=tk_hex,
                romfs_dir=romfs_dir,
                exefs_dir=exefs_dir,
            )
        except Exception as e:
            errors.append(f"NCA decryption failed: {e}")
            logger.exception("NCA decryption failed")

    if "psb" in stages and romfs_dir.exists():
        logger.info("[Stage 3/5] Extracting PSB archives from RomFS...")
        try:
            archives = find_psb_archives(romfs_dir)
            for stem, info_file, _body_file in archives:
                archive_out = archives_dir / stem
                try:
                    extract_psb_archive(info_file, archive_out, config)
                except Exception as e:
                    errors.append(f"PSB archive {stem} failed: {e}")
                    logger.exception("PSB archive %s failed", stem)
        except Exception as e:
            errors.append(f"PSB extraction failed: {e}")
            logger.exception("PSB extraction failed")

    if "image" in stages and archives_dir.exists():
        logger.info("[Stage 4/5] Extracting images from PSB files...")
        for subdir in sorted(archives_dir.iterdir()):
            if not subdir.is_dir():
                continue
            name_lower = subdir.name.lower()
            if name_lower.startswith("image"):
                for nested in sorted(subdir.iterdir()):
                    if nested.is_dir() and nested.name.lower().startswith("image"):
                        img_out = images_dir / subdir.name
                        try:
                            extract_images(nested, img_out, config)
                        except Exception as e:
                            errors.append(f"Image extraction failed: {e}")
                            logger.exception("Image extraction failed")
                        break

    if "script" in stages and archives_dir.exists():
        logger.info("[Stage 5/5] Dumping script bytecode...")
        bytecode_dumper = Path(__file__).resolve().parent / "dump_nut_bytecode.py"
        if not bytecode_dumper.exists():
            errors.append(f"Bytecode dumper not found: {bytecode_dumper}")
            logger.error("Bytecode dumper not found: %s", bytecode_dumper)
        else:
            for subdir in sorted(archives_dir.iterdir()):
                if not subdir.is_dir():
                    continue
                name_lower = subdir.name.lower()
                if name_lower.startswith("script"):
                    for nested in sorted(subdir.iterdir()):
                        if nested.is_dir() and nested.name.lower().startswith("script"):
                            script_out = scripts_dir / subdir.name
                            try:
                                dump_scripts(nested, script_out, bytecode_dumper)
                            except Exception as e:
                                errors.append(f"Script dump failed: {e}")
                                logger.exception("Script dump failed")
                            break

    logger.info("Moving results to output directory...")
    for src, dst in [
        (nca_dir, final_nca_dir),
        (exefs_dir, final_exefs_dir),
        (romfs_dir, final_romfs_dir),
        (images_dir, final_images_dir),
        (scripts_dir, final_scripts_dir),
    ]:
        if src.exists() and any(src.iterdir()):
            if dst.exists():
                shutil.rmtree(dst)
            shutil.move(str(src), str(dst))

    try:
        shutil.rmtree(work_root, ignore_errors=True)
    except Exception:
        pass

    config._prod_keys = saved_prod_keys
    config._title_keys = saved_title_keys

    generate_metadata(
        nsp_name=nsp_path.name,
        output_dir=output_dir,
        nca_dir=final_nca_dir if final_nca_dir.exists() else None,
        exefs_dir=final_exefs_dir if final_exefs_dir.exists() else None,
        romfs_dir=final_romfs_dir if final_romfs_dir.exists() else None,
        images_dir=final_images_dir if final_images_dir.exists() else None,
        scripts_dir=final_scripts_dir if final_scripts_dir.exists() else None,
        titlekeys=titlekeys,
        errors=errors,
    )

    if errors:
        logger.warning("Completed with %d error(s) for %s", len(errors), nsp_name)
    else:
        logger.info("Completed successfully for %s", nsp_name)

    return output_dir


ALL_STAGES = ["nca", "decrypt", "psb", "image", "script"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NSP Extraction Toolkit - Systematic NSP unpacking pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python nsp_toolkit.py --folder C:\\path\\to\\nsp\\files
  python nsp_toolkit.py --files game1.nsp game2.nsp
  python nsp_toolkit.py --gui
  python nsp_toolkit.py --folder . --stages nca decrypt
        """,
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--folder", type=Path, help="Folder containing NSP files"
    )
    input_group.add_argument(
        "--files", nargs="+", type=Path, help="Specific NSP files to process"
    )
    input_group.add_argument(
        "--gui", action="store_true", help="Open file/folder picker GUI"
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        default=ALL_STAGES,
        choices=ALL_STAGES,
        help=f"Extraction stages to run. Default: all ({', '.join(ALL_STAGES)})",
    )
    parser.add_argument(
        "--out", type=Path, help="Override output directory (default: ./out)"
    )
    parser.add_argument(
        "--hactool", type=Path, help="Override hactool.exe path"
    )
    parser.add_argument(
        "--psb-decompile", type=Path, help="Override PsbDecompile.exe path"
    )
    parser.add_argument(
        "--prod-keys", type=Path, help="Override prod.keys path"
    )
    parser.add_argument(
        "--title-keys", type=Path, help="Override title.keys path"
    )
    parser.add_argument(
        "--mdf-key", default="38757621acf82", help="MDF key prefix for PSB archives"
    )
    parser.add_argument(
        "--mdf-key-length", default="131", help="MDF key length for PSB archives"
    )
    parser.add_argument(
        "--fix-keys", action="store_true", help="Auto-fix prod.keys format issues"
    )
    args = parser.parse_args()

    config = ToolkitConfig()
    if args.out:
        config.out_dir = args.out.resolve()
    if args.hactool:
        config.hactool = args.hactool
    if args.psb_decompile:
        config.psb_decompile = args.psb_decompile
    if args.prod_keys:
        config.prod_keys = args.prod_keys
    if args.title_keys:
        config.title_keys = args.title_keys
    config.mdf_key = args.mdf_key
    config.mdf_key_length = args.mdf_key_length

    validation_errors = config.validate()
    if validation_errors:
        for err in validation_errors:
            logger.error("Config error: %s", err)
        logger.error(
            "Run setup.py first or provide tool paths via --hactool / --psb-decompile / --prod-keys"
        )
        return 1

    setup_logging(config.logs_dir, "extract")

    key_mgr = KeyManager(config.prod_keys, config.title_keys)
    if args.fix_keys:
        key_mgr.fix_prod_keys()
    key_mgr.load()

    nsp_files: list[Path] = []
    if args.folder:
        nsp_files = find_nsp_files(args.folder.resolve())
        if not nsp_files:
            logger.error("No NSP files found in %s", args.folder)
            return 1
    elif args.files:
        nsp_files = [f.resolve() for f in args.files]
        for f in nsp_files:
            if not f.exists():
                logger.error("File not found: %s", f)
                return 1
    elif args.gui:
        logger.info("Opening GUI file picker...")
        selected = select_files_gui()
        if not selected:
            folder = select_folder_gui()
            if not folder:
                logger.error("No files or folder selected")
                return 1
            nsp_files = find_nsp_files(folder)
            if not nsp_files:
                logger.error("No NSP files found in selected folder")
                return 1
        else:
            nsp_files = selected
    else:
        nsp_files = find_nsp_files(Path.cwd())
        if not nsp_files:
            parser.print_help()
            return 1

    logger.info("Found %d NSP file(s) to process", len(nsp_files))
    for f in nsp_files:
        logger.info("  - %s", f.name)

    total_errors = 0
    for idx, nsp_path in enumerate(nsp_files, 1):
        logger.info("\n[%d/%d] Processing: %s", idx, len(nsp_files), nsp_path.name)
        try:
            output = process_single_nsp(nsp_path, config, key_mgr, args.stages)
            logger.info("Output: %s", output)
        except Exception:
            total_errors += 1
            logger.exception("Fatal error processing %s", nsp_path.name)

    logger.info("=" * 60)
    logger.info("All done. Processed %d NSP file(s), %d fatal error(s)", len(nsp_files), total_errors)
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
