"""Embed a built site for local review without changing its publishable artifact."""

import argparse
import base64
import mimetypes
from pathlib import Path
import re


def create_preview(built: Path, destination: Path) -> None:
    document = (built / "index.html").read_text()
    scripts: list[str] = []

    def stylesheet(match: re.Match) -> str:
        return "<style>" + (built / match[1]).read_text() + "</style>"

    def script(match: re.Match) -> str:
        scripts.append((built / match[1]).read_text())
        return ""

    document = re.sub(r'<link rel="stylesheet" href="(\./assets/[^"]+)">', stylesheet, document)
    document = re.sub(r'<script src="(\./assets/[^"]+)" defer></script>', script, document)
    for path in sorted((built / "assets").iterdir()):
        if path.is_file():
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            document = document.replace("./assets/" + path.name, f"data:{mime};base64,{encoded}")
    document = document.replace(
        '<main class="wrap" id="main">',
        '<main class="wrap" id="main"><aside class="note" aria-label="Preview notice" '
        'style="padding:16px 0;border-bottom:1px solid var(--line)">'
        "Local, self-contained preview. The public site is not being deployed by this preview. "
        "External links and downloads may be blocked by the canvas sandbox; use the standalone "
        "site for navigation. Actual product images and the shared family mark are embedded below.</aside>",
        1,
    )
    document = document.replace("</body>", "".join("<script>" + js + "</script>" for js in scripts) + "</body>")
    payload = document.encode("utf-8")
    if len(payload) > 15_000_000:
        raise ValueError("Preview exceeds the 15 MB review limit.")
    destination.write_bytes(payload)
    print(f"Created self-contained preview: {destination} ({len(payload)} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("built", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    create_preview(args.built, args.destination)
