"""Build Infographic with the source-pinned catalog family theme."""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
from types import ModuleType

SITE = Path(__file__).resolve().parents[0]
ROOT = SITE.parents[0]


def load_theme() -> ModuleType:
    spec = importlib.util.spec_from_file_location("catalog_theme", SITE / "theme/build.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("The vendored catalog theme is missing.")
    theme = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(theme)
    theme.PAGES["infographic"] = {
        "name": "Infographic",
        "repository": "amplifier-smart-tool-infographic",
        "owner": "robotdad",
    }
    theme.__dict__["SPEC"] = "https://microsoft.github.io/amplifier-smart-tools/spec/"
    return theme


def asset_url(name: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", name):
        raise ValueError("Site assets must use a plain filename.")
    if not (SITE / "assets" / name).is_file():
        raise ValueError(f"Missing site asset: {name}")
    return "./assets/" + name


def gallery(config: dict, theme: ModuleType) -> str:
    sections = []
    for group in config["gallery"]:
        cards = []
        for sample in group["samples"]:
            image = asset_url(sample["image"])
            cards.append(
                f'<figure class="sample"><a href="{image}" aria-label="Open {theme.esc(sample["title"])}">'
                f'<img src="{image}" alt="{theme.esc(sample["alt"])}" width="{sample["width"]}" '
                f'height="{sample["height"]}" loading="lazy"></a><figcaption>'
                f'<p class="eyebrow">{theme.esc(sample["label"])}</p>'
                f"<h3>{theme.esc(sample['title'])}</h3><p>{theme.esc(sample['caption'])}</p>"
                f'<a href="{image}" download>Download display JPEG</a></figcaption></figure>'
            )
        sections.append(
            f'<section class="section" id="{theme.esc(group["id"])}"><div class="section-heading"><div>'
            f'<p class="eyebrow">Actual generated outputs</p><h2>{theme.esc(group["title"])}</h2></div>'
            f'<p>{theme.esc(group["description"])}</p></div><div class="sample-grid">{"".join(cards)}</div>'
            f'<p class="note">{theme.esc(group["quality"])}</p></section>'
        )
    return "".join(sections)


def build(output: Path) -> None:
    theme = load_theme()
    config = json.loads((SITE / "site.json").read_text())
    output = output.resolve()
    if output == ROOT or ROOT.is_relative_to(output) or output.is_relative_to(SITE):
        raise ValueError("Output must be separate from source.")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be empty. Choose a fresh generated-site directory.")
    args = argparse.Namespace(local=False, family_owner="microsoft")
    body = theme.tool_page(config, args)
    body = body.replace(
        '<section class="section two-col"><div><p class="eyebrow">How it works',
        gallery(config, theme) + '<section class="section two-col"><div><p class="eyebrow">How it works',
        1,
    )
    commands = "".join(theme.code_box(c["code"], c["title"], c["id"]) for c in config["commands"])
    extra = (
        '<section class="section two-col" id="local-use"><div><p class="eyebrow">On your machine</p>'
        '<h2>Browser, CLI,<br>or Python.</h2><p class="note">'
        "This is a static showcase, not a hosted generator. Run the tool locally. "
        "Open the full private URL printed by serve on the same machine. "
        "The server binds to 127.0.0.1; keep credentials out of this website.</p></div>"
        f'<div>{commands}</div></section><section class="section" id="limits">'
        '<p class="eyebrow">Read before you generate</p><h2>Useful tools. Honest limits.</h2>'
        f'<div class="detail-grid">{"".join(f"<article><h3>{theme.esc(t)}</h3><p>{theme.esc(p)}</p></article>" for t, p in config["limits"])}</div>'
        '</section><section class="section ownership"><h2>Independent tool. Shared foundations.</h2>'
        "<p>Infographic is an independent tool by Marc Goodner (robotdad), not a Microsoft product or endorsement. "
        "The Amplifier Smart Tools family theme and its MADE / Microsoft attribution are retained above and below.</p>"
        '<p>Functional inspiration: <a href="https://github.com/singh2/infographic-builder">Gurkaran Singh\'s '
        "infographic-builder</a>. Independently implemented without copying its source, prompts or assets.</p>"
        '<div class="compact-links"><a href="./assets/theme-LICENSE.txt">Theme MIT license</a>'
        "</div></section>"
    )
    body = body.replace(
        '<section class="section"><div class="section-heading"><div><p class="eyebrow">Part of',
        extra + '<section class="section"><div class="section-heading"><div><p class="eyebrow">Part of',
        1,
    )
    document = theme.document(config, body, args)
    document = document.replace(
        '<nav class="nav" aria-label="Main navigation">',
        '<nav class="nav" aria-label="Main navigation">'
        '<button class="motion-toggle" data-motion-toggle hidden type="button" '
        'aria-label="Toggle family mark motion" aria-pressed="false">Pause motion</button>',
        1,
    )
    document = document.replace(
        "</head>",
        '<link rel="stylesheet" href="./assets/infographic.css">'
        '<script src="./assets/infographic.js" defer></script>'
        '<link rel="canonical" href="https://robotdad.github.io/amplifier-smart-tool-infographic/"></head>',
    )
    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for filename in ("style.css", "site.js"):
        shutil.copy2(SITE / "theme" / filename, assets / filename)
    shutil.copy2(SITE / "theme/assets/mark-loop.png", assets / "mark-loop.png")
    shutil.copy2(SITE / "theme/assets/mark-loop.gif", assets / "mark-loop.gif")
    shutil.copy2(SITE / "theme/LICENSE", assets / "theme-LICENSE.txt")
    shutil.copytree(SITE / "assets", assets, dirs_exist_ok=True)
    (assets / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">'
        '<rect width="40" height="40" fill="#f6f4ee"/>'
        '<g fill="none" stroke="#92743a"><rect x="7" y="7" width="26" height="26"/>'
        '<rect x="11" y="11" width="18" height="18" transform="rotate(20 20 20)"/>'
        '<rect x="15" y="15" width="10" height="10" transform="rotate(40 20 20)"/></g></svg>'
    )
    (output / "index.html").write_text(document, encoding="utf-8")
    (output / ".nojekyll").touch()
    print(f"Built Infographic: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    build(parser.parse_args().output)
