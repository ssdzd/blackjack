"""Build the static browser version of the trainer (itch.io and other static hosts).

The browser build runs the unmodified FastAPI app inside the page under
Pyodide (CPython compiled to WebAssembly); web/boot.js and web/bridge.py
connect the frontend to it. This script assembles everything a static host
needs:

    dist/web/              the playable site: open index.html from any folder
    dist/blackjack-web.zip that folder zipped, ready to upload to itch.io
    dist/artifact/         (--artifact) the same game shaped for a claude.ai
                           Artifact: no document skeleton, fonts inlined

Usage:
    python scripts/build_web.py [--artifact] [--out dist]

Needs network access to registry.npmjs.org (Pyodide runtime) and PyPI
(wheels); both are cached under build/web-cache/.
"""

import argparse
import base64
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
WEB = ROOT / "web"
REQUIREMENTS = WEB / "requirements-web.txt"
CACHE = ROOT / "build" / "web-cache"

PYODIDE_VERSION = "314.0.7"
RUNTIME_FILES = (
    "pyodide.mjs",
    "pyodide.asm.mjs",
    "pyodide.asm.wasm",
    "python_stdlib.zip",
    "pyodide-lock.json",
)
APP_SOURCES = ("core", "api", "web")
BOOT_TAG = '<script type="module" src="boot.js"></script>'
MAIN_TAG = '<script type="module" src="js/main.js"></script>'
ARTIFACT_TITLE = "Blackjack Noir"

# itch.io's HTML5 limits (files after extraction, total extracted size).
ITCH_MAX_FILES = 1000
ITCH_MAX_BYTES = 500 * 1024 * 1024


def log(message: str) -> None:
    print(f"[build_web] {message}", flush=True)


def _shown(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


# ---- Inputs ----


def fetch_pyodide(cache: Path, version: str = PYODIDE_VERSION) -> Path:
    """Unpack the Pyodide runtime from npm; verifies npm's sha512 integrity."""
    target = cache / f"pyodide-{version}"
    if all((target / name).exists() for name in RUNTIME_FILES):
        return target

    meta = json.loads(_download(f"https://registry.npmjs.org/pyodide/{version}"))
    tarball = _download(meta["dist"]["tarball"])
    algorithm, _, expected = meta["dist"]["integrity"].partition("-")
    digest = base64.b64encode(hashlib.new(algorithm, tarball).digest()).decode()
    if digest != expected:
        raise SystemExit(f"pyodide {version}: tarball integrity check failed")

    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
        for name in RUNTIME_FILES:
            member = archive.extractfile(f"package/{name}")
            if member is None:
                raise SystemExit(f"pyodide {version}: {name} missing from tarball")
            (target / name).write_bytes(member.read())
    log(f"pyodide {version} runtime fetched")
    return target


def runtime_platform(runtime: Path) -> tuple[str, str]:
    """(wheel platform tag, Python X.Y) that this Pyodide runtime loads."""
    info = json.loads((runtime / "pyodide-lock.json").read_text())["info"]
    major, minor, *_ = info["python"].split(".")
    return f"pyemscripten_{info['abi_version']}_{info['arch']}", f"{major}.{minor}"


def pinned_requirements(path: Path = REQUIREMENTS) -> dict[str, str]:
    """{normalized name: version} from requirements-web.txt (every line pinned)."""
    pins = {}
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        name, sep, version = line.partition("==")
        if not sep:
            raise SystemExit(f"{path.name}: '{line}' must be pinned with ==")
        pins[_normalize(name)] = version.strip()
    return pins


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def fetch_wheels(cache: Path, platform: str, python: str) -> list[Path]:
    """Download the pinned wheels for the WebAssembly platform."""
    pins = pinned_requirements()
    key = hashlib.sha256((REQUIREMENTS.read_text() + platform).encode()).hexdigest()[:12]
    target = cache / f"wheels-{key}"
    wheels = sorted(target.glob("*.whl")) if target.exists() else []
    if len(wheels) != len(pins):
        target.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable, "-m", "pip", "download", "--quiet", "--no-deps",
                "--only-binary=:all:", "--platform", platform,
                "--python-version", python, "--implementation", "cp",
                "--abi", f"cp{python.replace('.', '')}",
                "-r", str(REQUIREMENTS), "-d", str(target),
            ],
            check=True,
        )
        wheels = sorted(target.glob("*.whl"))

    found = {}
    for wheel in wheels:
        name, version = wheel.name.split("-")[:2]
        found[_normalize(name)] = version
    if found != pins:
        raise SystemExit(f"wheels don't match {REQUIREMENTS.name}: {found} != {pins}")
    return wheels


# ---- Assembly ----


def inject_boot(html: str) -> str:
    """Load web/boot.js ahead of the frontend's entry point."""
    if MAIN_TAG not in html:
        raise ValueError(f"index.html no longer contains {MAIN_TAG!r}")
    return html.replace(MAIN_TAG, f"{BOOT_TAG}\n    {MAIN_TAG}", 1)


def pack_app() -> bytes:
    """Zip the Python the browser runs: core/, api/, web/ and config.py."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for top in APP_SOURCES:
            for path in sorted((ROOT / top).rglob("*.py")):
                if "__pycache__" not in path.parts:
                    archive.write(path, path.relative_to(ROOT).as_posix())
        archive.write(ROOT / "config.py", "config.py")
    return buffer.getvalue()


def assemble(out: Path, runtime: Path, wheels: list[Path]) -> None:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(FRONTEND, out, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    index = out / "index.html"
    index.write_text(inject_boot(index.read_text()))
    shutil.copy2(WEB / "boot.js", out / "boot.js")

    (out / "runtime").mkdir()
    for name in RUNTIME_FILES:
        shutil.copy2(runtime / name, out / "runtime" / name)
    (out / "wheels").mkdir()
    for wheel in wheels:
        shutil.copy2(wheel, out / "wheels" / wheel.name)
    (out / "app.zip").write_bytes(pack_app())

    manifest = {
        "pyodide": PYODIDE_VERSION,
        "runtime": "runtime/",
        "wheelDir": "wheels/",
        "wheels": [wheel.name for wheel in wheels],
        "app": "app.zip",
    }
    (out / "bundle.json").write_text(json.dumps(manifest, indent=2) + "\n")


def zip_site(site: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(site.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(site).as_posix())


def site_stats(site: Path) -> tuple[int, int]:
    files = [path for path in site.rglob("*") if path.is_file()]
    return len(files), sum(path.stat().st_size for path in files)


# ---- Artifact variant ----


def to_artifact_page(html: str, title: str = ARTIFACT_TITLE) -> str:
    """Reshape index.html for an Artifact, which supplies its own skeleton.

    Drops the doctype, <html>/<head>/<body> wrappers, the charset and
    viewport metas the skeleton provides, and the font preloads (the fonts
    are inlined instead), and renames the page.
    """
    head = re.search(r"<head>(.*?)</head>", html, re.S)
    body = re.search(r"<body[^>]*>(.*?)</body>", html, re.S)
    if not head or not body:
        raise ValueError("index.html needs <head> and <body> sections")
    dropped = re.compile(r'<meta charset|<meta name="viewport"|rel="preload"|<title>')
    head_lines = [line.strip() for line in head.group(1).splitlines()
                  if line.strip() and not dropped.search(line)]
    return "\n".join([f"<title>{title}</title>", *head_lines, body.group(1).strip(), ""])


def inline_fonts(css: str, fonts_dir: Path) -> str:
    """Embed the vendored woff2 files as data URIs."""

    def embed(match: re.Match) -> str:
        data = base64.b64encode((fonts_dir / match.group(1)).read_bytes()).decode()
        return f'url("data:font/woff2;base64,{data}")'

    return re.sub(r'url\("\.\./assets/fonts/([^"]+\.woff2)"\)', embed, css)


def make_artifact(site: Path, out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(site, out)
    index = out / "index.html"
    index.write_text(to_artifact_page(index.read_text()))
    tokens = out / "css" / "tokens.css"
    fonts = out / "assets" / "fonts"
    tokens.write_text(inline_fonts(tokens.read_text(), fonts))
    for font in fonts.glob("*.woff2"):
        font.unlink()


# ---- CLI ----


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    parser.add_argument("--artifact", action="store_true",
                        help="also build dist/artifact for a claude.ai Artifact")
    args = parser.parse_args(argv)

    runtime = fetch_pyodide(CACHE)
    platform, python = runtime_platform(runtime)
    wheels = fetch_wheels(CACHE, platform, python)
    log(f"{len(wheels)} wheels for {platform} (Python {python})")

    site = args.out / "web"
    assemble(site, runtime, wheels)
    count, size = site_stats(site)
    if count > ITCH_MAX_FILES or size > ITCH_MAX_BYTES:
        raise SystemExit(f"over itch.io's limits: {count} files, {size / 1e6:.1f} MB")
    archive = args.out / "blackjack-web.zip"
    zip_site(site, archive)
    log(f"{_shown(site)}: {count} files, {size / 1e6:.1f} MB")
    log(f"{_shown(archive)}: {archive.stat().st_size / 1e6:.1f} MB (itch.io upload)")

    if args.artifact:
        artifact = args.out / "artifact"
        make_artifact(site, artifact)
        count, size = site_stats(artifact)
        log(f"{_shown(artifact)}: {count} files, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
