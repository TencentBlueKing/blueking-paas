"""Download github/gitignore templates into ``git/assets``.

Usage (from the agent directory)::

    make update-gitignore-assets

Adding a language is a new row in :data:`~app_spark_agent.git.ignores.GITIGNORE_LANGUAGES`,
then re-running this. Files are overwritten in place so a git diff shows upstream drift.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

from app_spark_agent.git.ignores import (
    GITIGNORE_LANGUAGES,
    GitignoreLanguage,
    assets_root,
)

_USER_AGENT = "app-spark-agent-gitignore-sync"
_TIMEOUT_SECONDS = 30


def fetch_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"refusing to fetch {url}: only https is allowed")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})  # noqa: S310
    # Scheme is checked above; urlopen is otherwise flagged for allowing file:.
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310
        return response.read().decode("utf-8")


def download_templates(
    dest: Path,
    languages: tuple[GitignoreLanguage, ...] = GITIGNORE_LANGUAGES,
    *,
    fetch: Callable[[str], str] | None = None,
) -> list[Path]:
    """Write each GitHub source under ``dest``. Returns the files written."""
    get = fetch or fetch_url
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for spec in languages:
        path = dest.joinpath(*Path(spec.source).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            body = get(spec.raw_url())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"failed to download {spec.source}: HTTP {exc.code} from {spec.raw_url()}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"failed to download {spec.source} from {spec.raw_url()}: {exc}") from exc
        if not body.strip():
            raise RuntimeError(f"downloaded {spec.source} from {spec.raw_url()} but the body was empty")
        path.write_text(body, encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="assets directory (default: the package's git/assets)",
    )
    args = parser.parse_args(argv)

    dest = args.dest if args.dest is not None else assets_root()
    try:
        written = download_templates(dest)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)  # noqa: T201
        return 1
    for path in written:
        print(f"updated {path}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
