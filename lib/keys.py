import logging
import re
from pathlib import Path

logger = logging.getLogger("nsp_toolkit")


class KeyManager:
    def __init__(self, prod_keys_path: Path, title_keys_path: Path | None = None):
        self.prod_keys_path = prod_keys_path
        self.title_keys_path = title_keys_path
        self._prod_keys: dict[str, str] = {}
        self._title_keys: dict[str, str] = {}

    def load(self) -> None:
        self._prod_keys = self._load_keys_file(self.prod_keys_path)
        logger.info(
            "Loaded %d keys from %s", len(self._prod_keys), self.prod_keys_path.name
        )
        if self.title_keys_path and self.title_keys_path.exists():
            self._title_keys = self._load_keys_file(self.title_keys_path)
            logger.info(
                "Loaded %d keys from %s",
                len(self._title_keys),
                self.title_keys_path.name,
            )

    @staticmethod
    def _load_keys_file(path: Path) -> dict[str, str]:
        keys = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            m = re.match(r"^([A-Za-z0-9_]+)\s*=\s*([0-9a-fA-F]+)\s*$", line)
            if m:
                keys[m.group(1)] = m.group(2).lower()
        return keys

    def fix_prod_keys(self) -> int:
        fixed = 0
        content = self.prod_keys_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            m = re.match(
                r"^((?:mariko_master_kek_source|master_kek_source)_\w+)\s*=\s*([0-9a-fA-F]+)\s*$",
                line,
            )
            if m:
                name = m.group(1)
                val = m.group(2)
                if len(val) == 34 and val.lower().endswith("00"):
                    val = val[:32]
                    fixed += 1
                    logger.debug("Fixed key %s: removed trailing 00", name)
                new_lines.append(f"{name} = {val}")
            else:
                new_lines.append(line.rstrip())

        if fixed > 0:
            self.prod_keys_path.write_text("\n".join(new_lines), encoding="utf-8")
            logger.info("Fixed %d key(s) in prod.keys", fixed)
        return fixed

    @staticmethod
    def extract_titlekey_from_tik(tik_path: Path) -> str:
        data = tik_path.read_bytes()
        if len(data) < 0x190:
            raise ValueError(f"Tik file too small: {tik_path} ({len(data)} bytes)")
        titlekey = data[0x180:0x190]
        return titlekey.hex()

    def get_titlekey_for_rights_id(self, rights_id: str) -> str | None:
        return self._title_keys.get(rights_id.lower())

    @property
    def prod_keys(self) -> dict[str, str]:
        return self._prod_keys

    @property
    def title_keys(self) -> dict[str, str]:
        return self._title_keys
