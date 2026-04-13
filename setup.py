import shutil
import sys
from pathlib import Path


TOOLKIT_ROOT = Path(__file__).resolve().parent
NSP_ROOT = TOOLKIT_ROOT.parent


def copy_if_exists(src: Path, dst: Path, label: str) -> bool:
    if not src.exists():
        print(f"  [SKIP] {label}: source not found ({src})")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        count = sum(1 for _ in dst.rglob("*") if _.is_file())
        print(f"  [OK]   {label}: copied directory ({count} files)")
    else:
        shutil.copy2(src, dst)
        print(f"  [OK]   {label}: copied ({dst.name})")
    return True


def main() -> int:
    print("=" * 50)
    print("NSP Toolkit Setup")
    print("=" * 50)
    print(f"Toolkit root: {TOOLKIT_ROOT}")
    print(f"NSP root:     {NSP_ROOT}")
    print()

    print("[1/4] Copying hactool.exe...")
    copy_if_exists(
        NSP_ROOT / "hactool.exe",
        TOOLKIT_ROOT / "tools" / "hactool.exe",
        "hactool.exe",
    )

    print("[2/4] Copying PsbDecompile.exe...")
    psb_src = NSP_ROOT / "_tools" / "freemote_release" / "app" / "PsbDecompile.exe"
    copy_if_exists(
        psb_src,
        TOOLKIT_ROOT / "tools" / "PsbDecompile.exe",
        "PsbDecompile.exe",
    )

    print("[3/4] Copying key files...")
    copy_if_exists(
        NSP_ROOT / "prod.keys",
        TOOLKIT_ROOT / "keys" / "prod.keys",
        "prod.keys",
    )
    copy_if_exists(
        NSP_ROOT / "title.keys",
        TOOLKIT_ROOT / "keys" / "title.keys",
        "title.keys",
    )

    print("[4/4] Verifying setup...")
    errors = []
    required = [
        TOOLKIT_ROOT / "tools" / "hactool.exe",
        TOOLKIT_ROOT / "tools" / "PsbDecompile.exe",
        TOOLKIT_ROOT / "keys" / "prod.keys",
    ]
    for path in required:
        if not path.exists():
            errors.append(str(path))
            print(f"  [MISSING] {path}")
        else:
            print(f"  [OK]      {path.name}")

    if errors:
        print(f"\nSetup incomplete. {len(errors)} required file(s) missing.")
        print("Please manually copy the missing files and re-run setup.")
        return 1

    print("\nSetup complete! You can now run the toolkit:")
    print(f"  python {TOOLKIT_ROOT / 'nsp_toolkit.py'} --gui")
    print(f"  or double-click run.bat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
