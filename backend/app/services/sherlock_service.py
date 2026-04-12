"""Sherlock OSINT service — username investigation across social platforms.

Wraps the sherlock-project CLI to discover social media accounts
associated with a given username.
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

logger = logging.getLogger(__name__)

# Maximum time (seconds) to wait for sherlock to finish
SHERLOCK_TIMEOUT = 60

# Regex to extract "[+] <platform>: <url>" lines from sherlock output
_FOUND_PATTERN = re.compile(r"^\[\+\]\s+(.+?):\s+(https?://.+)$", re.MULTILINE)


class SherlockNotFoundError(RuntimeError):
    """Raised when the sherlock binary is not available on PATH."""


class SherlockTimeoutError(TimeoutError):
    """Raised when sherlock exceeds the configured timeout."""


def _validate_username(username: str) -> str:
    """Sanitise and validate the target username.

    Rules:
    - Must be 1-64 characters
    - Only alphanumeric, underscore, hyphen, and period allowed
    - No shell metacharacters
    """
    username = username.strip()
    if not username:
        raise ValueError("Username must not be empty")
    if len(username) > 64:
        raise ValueError("Username must be 64 characters or fewer")
    if not re.match(r"^[a-zA-Z0-9_.\-]+$", username):
        raise ValueError(
            "Username contains invalid characters. "
            "Only letters, digits, underscores, hyphens, and periods are allowed."
        )
    return username


def _parse_sherlock_output(stdout: str) -> dict[str, str]:
    """Extract {platform: url} pairs from sherlock's stdout."""
    results: dict[str, str] = {}
    for match in _FOUND_PATTERN.finditer(stdout):
        platform = match.group(1).strip()
        url = match.group(2).strip()
        results[platform] = url
    return results


async def investigate_username(
    username: str,
    *,
    timeout: int = SHERLOCK_TIMEOUT,
) -> dict[str, str]:
    """Run sherlock against *username* and return discovered profiles.

    Parameters
    ----------
    username:
        The target username to investigate (validated before execution).
    timeout:
        Maximum seconds to allow the sherlock process to run.

    Returns
    -------
    dict[str, str]
        Mapping of ``{platform_name: profile_url}`` for every platform
        where the username was found.

    Raises
    ------
    SherlockNotFoundError
        If the ``sherlock`` binary cannot be found on ``$PATH``.
    SherlockTimeoutError
        If the process exceeds *timeout* seconds.
    ValueError
        If the username fails validation.
    RuntimeError
        If sherlock exits with a non-zero return code.
    """
    username = _validate_username(username)

    sherlock_bin = shutil.which("sherlock")
    if sherlock_bin is None:
        raise SherlockNotFoundError(
            "sherlock binary not found on PATH. Install with: pip install sherlock-project"
        )

    with TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / f"{username}.txt"

        cmd = [
            sherlock_bin,
            username,
            "--print-found",
            "--no-color",
            "--output",
            str(output_file),
        ]

        logger.info("Running sherlock for username=%r (timeout=%ds)", username, timeout)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmpdir,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except TimeoutError:
            # Kill the zombie process before raising
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass
            raise SherlockTimeoutError(
                f"Sherlock timed out after {timeout}s for username={username!r}"
            ) from None

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        if process.returncode != 0:
            logger.error(
                "Sherlock failed (rc=%d) for username=%r: %s",
                process.returncode,
                username,
                stderr[:500],
            )
            raise RuntimeError(f"Sherlock exited with code {process.returncode}: {stderr[:300]}")

        results = _parse_sherlock_output(stdout)
        logger.info(
            "Sherlock found %d profiles for username=%r",
            len(results),
            username,
        )
        return results
