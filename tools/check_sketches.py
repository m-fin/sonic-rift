#!/usr/bin/env python3
"""Check the committed sketches gallery against sketches/build.py.

Rebuilds the HTML into a temporary directory and diffs it against the pages
in sketches/. Also checks that every relative link or asset referenced from
sketches/index.html exists inside the repo.

The audio render is not part of this check. The pages do not embed samples,
and tools/check_audio.py already measures the WAVs.
"""

from __future__ import annotations

import difflib
import importlib.util
import os
import sys
import tempfile
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

MAX_DIFF_LINES = 80

_BUILD = None


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_build():
    """Import sketches/build.py without running its audio render."""

    global _BUILD
    if _BUILD is not None:
        return _BUILD
    path = os.path.join(repo_root(), "sketches", "build.py")
    spec = importlib.util.spec_from_file_location("sketches_build", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _BUILD = module
    return module


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def diff_summary(rel: str, committed: bytes, generated: bytes) -> str:
    """Short unified diff, committed on the left and build.py on the right."""

    header = f"{rel} differs from sketches/build.py output"
    try:
        committed_text = committed.decode("utf-8")
        generated_text = generated.decode("utf-8")
    except UnicodeDecodeError:
        return (
            f"{header} ({len(committed)} bytes committed, {len(generated)} bytes generated; not valid UTF-8)"
        )
    if committed_text == generated_text:
        return f"{header} ({len(committed)} bytes committed, {len(generated)} bytes generated)"
    lines = list(
        difflib.unified_diff(
            committed_text.splitlines(keepends=True),
            generated_text.splitlines(keepends=True),
            fromfile=f"{rel} (committed)",
            tofile=f"{rel} (build.py)",
        )
    )
    body = "".join(lines).rstrip("\n")
    body_lines = body.splitlines()
    if len(body_lines) > MAX_DIFF_LINES:
        hidden = len(body_lines) - MAX_DIFF_LINES
        body = "\n".join(body_lines[:MAX_DIFF_LINES] + [f"... diff truncated, {hidden} more lines"])
    return f"{header}\n{body}"


def check_drift(root: str) -> list[str]:
    """Rebuild the gallery in a temp directory and compare it to ``root/sketches``."""

    build = load_build()
    sketches = os.path.join(root, "sketches")
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        files = build.write_gallery(tmp)
        for name in files:
            rel = f"sketches/{name}"
            committed_path = os.path.join(sketches, name)
            if not os.path.isfile(committed_path):
                failures.append(f"{rel} is missing; sketches/build.py would write it")
                continue
            try:
                committed = _read_bytes(committed_path)
            except OSError as exc:
                failures.append(f"{rel} could not be read: {exc}")
                continue
            generated = _read_bytes(os.path.join(tmp, name))
            if committed != generated:
                failures.append(diff_summary(rel, committed, generated))
    return failures


class _RefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"href", "src"} and value is not None:
                self.refs.append((key, value))


def page_refs(html: str) -> list[tuple[str, str]]:
    parser = _RefParser()
    parser.feed(html)
    parser.close()
    return parser.refs


def _outside_repo(root: str, target: str) -> bool:
    root = os.path.abspath(root)
    try:
        return os.path.commonpath([root, target]) != root
    except ValueError:
        return True


def check_links(root: str) -> list[str]:
    """Fail when sketches/index.html points at a relative path that is not in the repo.

    ``http``, ``https``, and other absolute URLs are skipped. Fragment-only links
    stay on the page. A path that resolves outside ``root`` fails even when that
    file exists on disk.
    """

    index_path = os.path.join(root, "sketches", "index.html")
    if not os.path.isfile(index_path):
        return ["sketches/index.html is missing"]
    try:
        html = _read_bytes(index_path).decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"sketches/index.html could not be read: {exc}"]

    page_dir = os.path.dirname(os.path.abspath(index_path))
    failures: list[str] = []
    for key, value in page_refs(html):
        raw = value.strip()
        where = f"sketches/index.html {key}={value!r}"
        if raw == "":
            failures.append(f"{where} is empty")
            continue
        parts = urlparse(raw)
        if parts.scheme or parts.netloc:
            continue
        path = unquote(parts.path)
        if path == "":
            continue
        target = os.path.abspath(os.path.normpath(os.path.join(page_dir, path)))
        if _outside_repo(root, target):
            failures.append(f"{where} resolves outside the repo ({target})")
            continue
        if not os.path.exists(target):
            failures.append(f"{where} is not in the repo (looked for {os.path.relpath(target, root)})")
    return failures


def check_sketches(root: str | None = None) -> list[str]:
    root = repo_root() if root is None else root
    return check_drift(root) + check_links(root)


def format_report(failures: list[str]) -> str:
    if not failures:
        return "sketches gallery matches build.py; relative links in sketches/index.html resolve"
    return f"sketches gallery check failed ({len(failures)}):\n\n" + "\n\n".join(failures)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) > 1 or (argv and argv[0] in {"-h", "--help"}):
        print("usage: python tools/check_sketches.py [root]", file=sys.stderr)
        return 2
    root = argv[0] if argv else repo_root()
    failures = check_sketches(root)
    print(format_report(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
