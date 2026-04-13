import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("nsp_toolkit")


class CommandError(RuntimeError):
    def __init__(self, cmd: list[str], returncode: int, stderr: str = ""):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"Command failed (exit {returncode}): {' '.join(cmd)}"
        )


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    timeout: int | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    cmd_str = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    logger.debug("Running: %s", cmd_str)

    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.stdout:
        for line in result.stdout.strip().splitlines():
            logger.debug("  stdout: %s", line)
    if result.stderr:
        for line in result.stderr.strip().splitlines():
            if "[WARN]" in line:
                logger.warning("  hactool: %s", line.strip())
            else:
                logger.debug("  stderr: %s", line)

    if check and result.returncode != 0:
        raise CommandError(cmd, result.returncode, result.stderr)

    return result
