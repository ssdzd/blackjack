"""Helpers in scripts/build_web.py, and what the browser build needs from the frontend."""

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("build_web", ROOT / "scripts" / "build_web.py")
build_web = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_web)


class TestFrontendIsPortable:
    """Static hosts serve the game from a sub-folder, so no path may be root-absolute."""

    def test_index_has_no_root_absolute_asset_paths(self):
        html = (ROOT / "frontend" / "index.html").read_text()
        assert not re.search(r'(href|src)="/(?!/)', html)

    def test_stylesheets_have_no_root_absolute_urls(self):
        for css in (ROOT / "frontend" / "css").glob("*.css"):
            assert not re.search(r'url\(\s*["\']?/(?!/)', css.read_text()), css.name

    def test_index_keeps_the_entry_point_the_build_hooks(self):
        assert build_web.MAIN_TAG in (ROOT / "frontend" / "index.html").read_text()


class TestInjectBoot:
    def test_boot_loads_before_the_frontend(self):
        html = build_web.inject_boot(f"<body>\n{build_web.MAIN_TAG}\n</body>")
        assert html.index(build_web.BOOT_TAG) < html.index(build_web.MAIN_TAG)

    def test_missing_entry_point_is_an_error(self):
        with pytest.raises(ValueError):
            build_web.inject_boot("<body></body>")


class TestArtifactPage:
    HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blackjack Trainer</title>
    <link rel="preload" href="assets/fonts/A.woff2" as="font" type="font/woff2" crossorigin>
    <link rel="stylesheet" href="css/tokens.css">
</head>
<body>
    <div id="app"></div>
    <script type="module" src="js/main.js"></script>
</body>
</html>"""

    def test_drops_the_skeleton_and_keeps_the_page(self):
        page = build_web.to_artifact_page(self.HTML, "Blackjack Noir")
        assert page.startswith("<title>Blackjack Noir</title>")
        for gone in ("<!DOCTYPE", "<html", "<head>", "<body>", "<meta", "preload", "Blackjack Trainer"):
            assert gone not in page
        for kept in ('href="css/tokens.css"', '<div id="app">', 'src="js/main.js"'):
            assert kept in page

    def test_archives_are_packed_as_json(self, tmp_path):
        import base64
        import json

        (tmp_path / "wheels").mkdir()
        (tmp_path / "wheels" / "a-1.0-py3-none-any.whl").write_bytes(b"PK\x03\x04wheel")
        (tmp_path / "app.zip").write_bytes(b"PK\x03\x04app")
        (tmp_path / "boot.js").write_text("// untouched")

        packed = build_web.pack_archives(tmp_path)

        assert packed == {
            "app.zip": "packed/app.zip.json",
            "wheels/a-1.0-py3-none-any.whl": "packed/wheels/a-1.0-py3-none-any.whl.json",
        }
        record = json.loads((tmp_path / "packed" / "app.zip.json").read_text())
        assert base64.b64decode(record["base64"]) == b"PK\x03\x04app"
        assert not (tmp_path / "app.zip").exists()
        assert (tmp_path / "boot.js").exists()

    def test_fonts_become_data_uris(self, tmp_path):
        (tmp_path / "A.woff2").write_bytes(b"wOF2fake")
        css = build_web.inline_fonts('src: url("../assets/fonts/A.woff2") format("woff2");', tmp_path)
        assert 'url("data:font/woff2;base64,d09GMmZha2U=")' in css


class TestRequirements:
    def test_every_wheel_is_pinned(self):
        pins = build_web.pinned_requirements()
        assert pins["pydantic"] and pins["fastapi"] and pins["transitions"]

    def test_unpinned_line_is_rejected(self, tmp_path):
        bad = tmp_path / "req.txt"
        bad.write_text("fastapi>=0.1\n")
        with pytest.raises(SystemExit):
            build_web.pinned_requirements(bad)
