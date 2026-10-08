"""Offline checks for the static Pages artifact, not generation or visual quality."""

import base64
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from urllib.parse import urljoin, urlsplit

from PIL import Image
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://robotdad.github.io/amplifier-smart-tool-infographic/"


class Page(HTMLParser):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.nodes: list[tuple[str, dict]] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.nodes.append((tag, dict(attrs)))


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("infographic-site") / "output"
    subprocess.run([sys.executable, str(ROOT / "site/build.py"), "--output", str(output)], check=True)
    return output


@pytest.fixture
def builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("infographic_site", ROOT / "site/build.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vendored_theme_has_pinned_provenance() -> None:
    provenance = json.loads((ROOT / "site/provenance.json").read_text())
    assert provenance["theme"]["commit"] == "59339a5c52aa909f7f7e18c2c92de82ec66eae4c"
    for file in provenance["theme"]["files"]:
        assert hashlib.sha256((ROOT / file["path"]).read_bytes()).hexdigest() == file.get(
            "vendored_sha256", file["sha256"]
        )


def test_all_local_links_and_fragments_resolve_under_project_base(built: Path) -> None:
    page = Page((built / "index.html").read_text())
    ids = {attrs["id"] for _, attrs in page.nodes if "id" in attrs}
    for _, attrs in page.nodes:
        for key in ("href", "src", "poster"):
            if key not in attrs:
                continue
            value = attrs[key]
            if value.startswith("#"):
                assert value[1:] in ids
            elif not urlsplit(value).scheme:
                resolved = urlsplit(urljoin(BASE, value))
                assert resolved.path.startswith("/amplifier-smart-tool-infographic/")
                relative = resolved.path.removeprefix("/amplifier-smart-tool-infographic/")
                assert (built / relative).is_file(), value


def test_canonical_family_and_independent_identity(built: Path) -> None:
    html = (built / "index.html").read_text()
    for text in (
        "https://microsoft.github.io/amplifier-smart-tools/",
        "https://microsoft.github.io/amplifier-smart-tools-catalog/",
        "https://microsoft.github.io/amplifier-smart-tools/spec/",
        "Microsoft Office of the CTO",
        "MADE",
        "not a Microsoft product or endorsement",
        f'rel="canonical" href="{BASE}"',
    ):
        assert text in html
    assert "https://robotdad.github.io/amplifier-smart-tools/" not in html
    assert (built / "assets/theme-LICENSE.txt").read_bytes() == (ROOT / "site/theme/LICENSE").read_bytes()


def test_copy_targets_and_accessible_images(built: Path) -> None:
    page = Page((built / "index.html").read_text())
    ids = [attrs["id"] for _, attrs in page.nodes if "id" in attrs]
    assert len(ids) == len(set(ids))
    for tag, attrs in page.nodes:
        if "data-copy" in attrs:
            assert attrs["data-copy"] in ids
        if tag == "img":
            assert "alt" in attrs
            assert int(attrs["width"]) > 0
            assert int(attrs["height"]) > 0
    assert (built / ".nojekyll").is_file()


def test_approved_derivatives_decode_and_match_provenance(built: Path) -> None:
    provenance = json.loads((ROOT / "site/provenance.json").read_text())
    assert len(provenance["samples"]) == 4
    for sample in provenance["samples"]:
        file = built / "assets" / sample["file"]
        assert file.read_bytes() == (ROOT / "site/assets" / sample["file"]).read_bytes()
        assert hashlib.sha256(file.read_bytes()).hexdigest() == sample["display_jpeg_sha256"]
        with Image.open(file) as image:
            image.load()
            assert image.size == (sample["width"], sample["height"])
            assert image.format == "JPEG"
    assert sum((built / "assets" / s["file"]).stat().st_size for s in provenance["samples"]) < 2_000_000


def test_copy_preserves_capability_and_quality_boundaries(built: Path) -> None:
    html = (built / "index.html").read_text()
    for text in (
        "Strong defaults. Not rails.",
        "Freeform",
        "NEEDS WORK",
        "not human acceptance",
        "earlier sibling revision failed",
        "not a hosted generator",
        "No MCP App yet",
        "OpenAI",
        "Anthropic",
        "Gemini",
        "ChatGPT OAuth",
        "GitHub Copilot",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "0.22.0",
        "Python 3.13+",
        "@main",
        "infographic serve --store ./results",
        "127.0.0.1",
        "Download display JPEG",
        "not the original PNGs",
    ):
        assert text in html
    assert "<form" not in html
    assert "api_key=" not in html


def test_only_approved_static_assets_are_published(built: Path) -> None:
    expected = {"index.html", ".nojekyll"}
    expected |= {"assets/" + p.name for p in (ROOT / "site/assets").iterdir() if p.is_file()}
    expected |= {
        "assets/" + name
        for name in ("style.css", "site.js", "mark-loop.png", "mark-loop.gif", "theme-LICENSE.txt", "favicon.svg")
    }
    assert {str(p.relative_to(built)) for p in built.rglob("*") if p.is_file()} == expected
    for file in built.rglob("*"):
        if file.suffix in {".html", ".json", ".js", ".css", ".txt"}:
            text = file.read_text()
            assert "/home/" not in text
            assert ".work/" not in text
            assert "result.json" not in text


def test_no_rejected_product_brand_files_or_references(built: Path) -> None:
    for directory in (ROOT / "site", built):
        for path in directory.rglob("*"):
            assert not path.name.startswith(("infographic-icon-", "infographic-logo-"))
    for path in built.rglob("*"):
        if path.is_file() and path.suffix in {".html", ".js", ".css", ".json"}:
            text = path.read_text()
            for rejected in (
                "brand-video",
                "brand-replay",
                "brand-static",
                "tool-logo",
                "View static logo",
                "3281eefd",
            ):
                assert rejected not in text
    assert not (built / "assets/provenance.json").exists()
    assert not list(built.rglob("*.mp4"))
    assert not list(built.rglob("*.mov"))
    assert "brand" not in json.loads((ROOT / "site/site.json").read_text())
    assert "brand" not in json.loads((ROOT / "site/provenance.json").read_text())


def test_actual_output_hero_and_family_identity_remain(built: Path) -> None:
    html = (built / "index.html").read_text()
    page = Page(html)
    videos = [attrs for tag, attrs in page.nodes if tag == "video"]
    assert not videos
    assert "data-motion-src" in html
    assert "data-motion-toggle" in html
    assert "Actual Infographic output, not a logo or interface screenshot" in html
    assert '<div class="product-image"><a href="./assets/blue-hour.jpg"' in html
    assert 'rel="icon" href="./assets/favicon.svg"' in html
    assert "provenance.json" not in html
    for name in ("mark-loop.png", "mark-loop.gif"):
        assert (built / "assets" / name).read_bytes() == (ROOT / "site/theme/assets" / name).read_bytes()
    assert "prefers-reduced-motion: reduce" in (built / "assets/site.js").read_text()


def test_build_refuses_source_or_nonempty_output(builder: ModuleType, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="separate from source"):
        builder.build(ROOT / "site")
    sentinel = tmp_path / "keep.txt"
    sentinel.write_text("preserve")
    with pytest.raises(ValueError, match="empty"):
        builder.build(tmp_path)
    assert sentinel.read_text() == "preserve"


def test_asset_names_cannot_escape(builder: ModuleType) -> None:
    with pytest.raises(ValueError, match="plain filename"):
        builder.asset_url("../private.png")
    with pytest.raises(ValueError, match="Missing site asset"):
        builder.asset_url("not-present.png")


def test_workflow_builds_prs_and_restricts_publication() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/website.yml").read_text())
    events = workflow.get("on", workflow.get(True))
    assert "workflow_run" not in events
    assert "pull_request" in events
    assert events["workflow_dispatch"]["inputs"]["publish"]["default"] is False
    assert workflow["permissions"] == {"contents": "read"}
    deploy = workflow["jobs"]["deploy"]
    assert "refs/heads/main" in deploy["if"]
    assert "inputs.publish" in deploy["if"]
    assert "pull_request" not in deploy["if"]
    assert deploy["permissions"] == {"pages": "write", "id-token": "write"}
    assert workflow["jobs"]["build"]["steps"][0]["with"]["persist-credentials"] is False


def test_self_contained_preview_preserves_actual_embedded_bytes(built: Path, tmp_path: Path) -> None:
    original = (built / "index.html").read_bytes()
    destination = tmp_path / "preview.html"
    subprocess.run([sys.executable, str(ROOT / "site/preview.py"), str(built), str(destination)], check=True)
    assert destination.stat().st_size < 15_000_000
    assert (built / "index.html").read_bytes() == original
    html = destination.read_text()
    assert "canvas sandbox" in html
    assert "./assets/" not in html
    page = Page(html)
    count = 0
    for _, attrs in page.nodes:
        for value in attrs.values():
            if isinstance(value, str) and value.startswith("data:") and ";base64," in value:
                data = base64.b64decode(value.split(";base64,", 1)[1], validate=True)
                assert any(data == path.read_bytes() for path in (built / "assets").iterdir())
                count += 1
    assert count >= 15
    assert "brandVideo" not in html
    assert "data:video/" not in html
