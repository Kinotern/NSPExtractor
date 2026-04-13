from pathlib import Path


class ToolkitConfig:
    def __init__(self, toolkit_root: Path | None = None):
        self.root = toolkit_root or Path(__file__).resolve().parent.parent
        self.tools_dir = self.root / "tools"
        self.keys_dir = self.root / "keys"
        self.out_dir = self.root / "out"
        self.logs_dir = self.root / "logs"
        self.work_dir = self.root.parent / "_nsp_work"

        self._hactool: Path | None = None
        self._psb_decompile: Path | None = None
        self._prod_keys: Path | None = None
        self._title_keys: Path | None = None

        self.mdf_key = "38757621acf82"
        self.mdf_key_length = "131"

    @property
    def hactool(self) -> Path:
        if self._hactool:
            return self._hactool
        local = self.tools_dir / "hactool.exe"
        if local.exists():
            return local
        parent_tool = self.root.parent / "hactool.exe"
        if parent_tool.exists():
            return parent_tool
        raise FileNotFoundError(
            f"hactool.exe not found in {local} or {parent_tool}"
        )

    @hactool.setter
    def hactool(self, path: Path | str):
        self._hactool = Path(path).resolve()

    @property
    def psb_decompile(self) -> Path:
        if self._psb_decompile:
            return self._psb_decompile
        local = self.tools_dir / "PsbDecompile.exe"
        if local.exists():
            return local
        local_fallback = self.tools_dir / "freemote" / "PsbDecompile.exe"
        if local_fallback.exists():
            return local_fallback
        parent_tool = (
            self.root.parent / "_tools" / "freemote_release" / "app" / "PsbDecompile.exe"
        )
        if parent_tool.exists():
            return parent_tool
        raise FileNotFoundError(
            f"PsbDecompile.exe not found in {local} or {parent_tool}"
        )

    @psb_decompile.setter
    def psb_decompile(self, path: Path | str):
        self._psb_decompile = Path(path).resolve()

    @property
    def prod_keys(self) -> Path:
        if self._prod_keys:
            return self._prod_keys
        local = self.keys_dir / "prod.keys"
        if local.exists():
            return local
        parent_key = self.root.parent / "prod.keys"
        if parent_key.exists():
            return parent_key
        raise FileNotFoundError(
            f"prod.keys not found in {local} or {parent_key}"
        )

    @prod_keys.setter
    def prod_keys(self, path: Path | str):
        self._prod_keys = Path(path).resolve()

    @property
    def title_keys(self) -> Path | None:
        if self._title_keys:
            return self._title_keys
        local = self.keys_dir / "title.keys"
        if local.exists():
            return local
        parent_key = self.root.parent / "title.keys"
        if parent_key.exists():
            return parent_key
        return None

    @title_keys.setter
    def title_keys(self, path: Path | str):
        self._title_keys = Path(path).resolve()

    def validate(self) -> list[str]:
        errors = []
        try:
            _ = self.hactool
        except FileNotFoundError as e:
            errors.append(str(e))
        try:
            _ = self.psb_decompile
        except FileNotFoundError as e:
            errors.append(str(e))
        try:
            _ = self.prod_keys
        except FileNotFoundError as e:
            errors.append(str(e))
        return errors
