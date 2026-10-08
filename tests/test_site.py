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
APPROVED_BRAND = {
    "infographic-picture-icon-512.png": "f7a2b6c52e6072a345974565fa65f46de9f857f80141a0b9cafe4d659e520d89",
    "infographic-picture-icon-32.png": "27c626d31e715b8ed066c12ae09fccb4cd33ff14bd97649a5d1ae7263d5f451c",
    "infographic-picture-icon-16.png": "c5fa3b34230a0dcd836121374ab0992ddf3ec792635e8425c042a15331e16dcb",
    "infographic-picture-poster.png": "17d76bf189ed005d1d5166606764287fb84887cb34884e27e655f2198c644faf",
    "infographic-picture-animation.mp4": "23348501104fb49d4cc9c592cec1dd48e488b47c242213fe8554f831048eb0c9",
}


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
        "assets/" + name for name in ("style.css", "site.js", "mark-loop.png", "mark-loop.gif", "theme-LICENSE.txt")
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
    assert [p.name for p in built.rglob("*.mp4")] == ["infographic-picture-animation.mp4"]
    assert not list(built.rglob("*.mov"))
    assert "brand" not in json.loads((ROOT / "site/site.json").read_text())
    assert not (built / "assets/favicon.svg").exists()
    assert {p.name for p in (ROOT / "site/assets").glob("*.png")} == {
        name for name in APPROVED_BRAND if name.endswith(".png")
    }


def test_actual_output_hero_and_family_identity_remain(built: Path) -> None:
    html = (built / "index.html").read_text()
    page = Page(html)
    videos = [attrs for tag, attrs in page.nodes if tag == "video"]
    assert len(videos) == 1
    assert "data-motion-src" in html
    assert "data-motion-toggle" in html
    assert "Actual Infographic output, not a logo or interface screenshot" in html
    assert '<div class="product-image"><a href="./assets/blue-hour.jpg"' in html
    icons = [attrs for tag, attrs in page.nodes if tag == "link" and attrs.get("rel") == "icon"]
    assert {a["href"] for a in icons} == {
        "./assets/infographic-picture-icon-16.png",
        "./assets/infographic-picture-icon-32.png",
    }
    assert "provenance.json" not in html
    for name in ("mark-loop.png", "mark-loop.gif"):
        assert (built / "assets" / name).read_bytes() == (ROOT / "site/theme/assets" / name).read_bytes()
    assert "prefers-reduced-motion: reduce" in (built / "assets/site.js").read_text()


def test_approved_brand_bytes_and_alpha(built: Path) -> None:
    brand = json.loads((ROOT / "site/provenance.json").read_text())["brand"]
    assert brand["revision"] == "ddadd4d362da4a52bfcfe64a38eeab42"
    assert brand["files"] == APPROVED_BRAND
    assert brand["agent_binding"] == brand["agent_engine"] == "0.20.0"
    assert brand["author_effort"] == "default/unset"
    for name, digest in APPROVED_BRAND.items():
        data = (built / "assets" / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        assert data == (ROOT / "site/assets" / name).read_bytes()
        if name.endswith(".png"):
            with Image.open(built / "assets" / name) as image:
                image.load()
                if "-icon-" in name:
                    size = int(name.split("-")[-1].split(".")[0])
                    assert image.size == (size, size)
                    assert image.mode == "RGBA"
                    assert image.getchannel("A").getextrema() == (0, 255)
                else:
                    assert image.size == (1920, 1080)


def test_brand_starts_static_with_native_controls_and_explicit_play(built: Path) -> None:
    html = (built / "index.html").read_text()
    page = Page(html)
    video = next(attrs for tag, attrs in page.nodes if tag == "video")
    assert video["id"] == "identity-video"
    assert video["preload"] == "none"
    assert video["poster"] == "./assets/infographic-picture-poster.png"
    assert "controls" in video
    assert "playsinline" in video
    assert "autoplay" not in video
    assert "loop" not in video
    button = next(attrs for _, attrs in page.nodes if attrs.get("id") == "identity-play")
    assert "hidden" in button
    assert button["aria-controls"] == "identity-video"
    assert "Brand animation / Made with Unfold" in html
    assert "not an Infographic-generated example" in html
    assert "View static PNG" in html
    assert "5.5-second silent" in html
    js = (built / "assets/infographic.js").read_text()
    assert "data-motion-toggle" not in js
    assert "data-motion-src" not in js
    assert "[hidden] { display: none !important; }" in (built / "assets/infographic.css").read_text()


@pytest.mark.parametrize("reduced", [False, True])
def test_brand_motion_event_lifecycle(built: Path, reduced: bool) -> None:
    # A DOM/media double checks event wiring; real playback is independently browser-reviewed.
    script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function element(extra = {}) {
  return Object.assign({listeners: {}, hidden: true, textContent: '',
    addEventListener(name, callback) { this.listeners[name] = callback; }}, extra);
}
let plays = 0, loads = 0, fails = false;
const video = element({paused: true, currentTime: 0,
  async play() {
    plays++;
    if (fails) throw new Error('denied');
    this.paused = false; this.listeners.play();
  },
  pause() { this.paused = true; this.listeners.pause(); },
  load() { loads++; this.paused = true; this.currentTime = 0; }
});
const button = element(), status = element();
const media = element({matches: REDUCED});
const elements = {'identity-video': video, 'identity-play': button, 'identity-status': status};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), {
  document: {documentElement: {classList: {add() {}}}, getElementById: id => elements[id]},
  window: {matchMedia: () => media}
});
(async () => {
  assert.equal(plays, 0);
  assert.equal(video.paused, true);
  assert.equal(button.hidden, false);
  await button.listeners.click();
  assert.equal(plays, 1);
  assert.equal(button.textContent, 'Pause animation');
  await button.listeners.click();
  assert.equal(video.paused, true);
  assert.equal(button.textContent, 'Replay animation');
  video.currentTime = 3;
  await button.listeners.click();
  assert.equal(video.currentTime, 0);
  assert.equal(plays, 2);
  video.paused = true; video.listeners.ended();
  assert.equal(loads, 1);
  assert.equal(plays, 2);
  assert.equal(button.textContent, 'Replay animation');
  await video.play(); // Native controls update the independent custom button.
  assert.equal(button.textContent, 'Pause animation');
  media.listeners.change({matches: true});
  assert.equal(video.paused, true);
  media.listeners.change({matches: false});
  assert.equal(plays, 3); // Preference changes never start playback.
  fails = true;
  await button.listeners.click();
  assert.match(status.textContent, /native controls/);
  video.listeners.error();
  assert.match(status.textContent, /static PNG/);
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    subprocess.run(
        [
            "node",
            "-e",
            script.replace("REDUCED", json.dumps(reduced)),
            str(built / "assets/infographic.js"),
        ],
        check=True,
    )


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
    assert "data:video/mp4;base64," in html
