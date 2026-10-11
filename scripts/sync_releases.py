#!/usr/bin/env python3
"""Verify public releases and update only their cask version and checksum."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
SHA256 = re.compile(r"[a-f0-9]{64}")


def fetch(url):
    request = Request(url, headers={"User-Agent": "jerrylusato-homebrew-tap"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def validate_release(config, release, manifest):
    version = manifest.get("version", "")
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("Expected a stable semantic version")
    tag = "v" + version
    if release.get("draft") or release.get("prerelease") or release.get("tag_name") != tag:
        raise ValueError("Expected a published stable release with a matching tag")
    if manifest.get("app") != config["app"] or manifest.get("tag") != tag:
        raise ValueError("Manifest app/tag mismatch")
    build = manifest.get("build")
    if type(build) is not int or build < 1:
        raise ValueError("Invalid build number")
    if not re.fullmatch(r"[a-f0-9]{40}", manifest.get("commit", "")):
        raise ValueError("Invalid source commit")
    signing = manifest.get("signing")
    if signing not in config["workflows"] or manifest.get("notarized") is not (signing == "developer-id"):
        raise ValueError("Missing or inconsistent signing status")
    filename = config["filename"].format(version=version)
    prefix = f'https://github.com/{config["repository"]}/releases/download/{tag}/'
    assets = {item["name"]: item for item in release.get("assets", [])}
    for name in (filename, "SHA256SUMS", "release-manifest.json"):
        if assets.get(name, {}).get("browser_download_url") != prefix + name:
            raise ValueError("Missing asset or untrusted download destination")
    files = [item for item in manifest.get("files", []) if item.get("name") == filename]
    if len(files) != 1:
        raise ValueError("Expected exactly one matching package")
    file = files[0]
    digest = file.get("sha256", "")
    size = file.get("size")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ValueError("Invalid SHA-256 digest")
    if type(size) is not int or size <= 0 or assets[filename].get("size") != size:
        raise ValueError("Invalid package size")
    if assets[filename].get("digest") not in (None, "sha256:" + digest):
        raise ValueError("GitHub digest mismatch")
    return filename, prefix, digest, size


def update_cask(content, version, digest):
    previous = re.search(r'^  version "([0-9]+\.[0-9]+\.[0-9]+)"$', content, re.M)
    if not previous:
        raise ValueError("Cannot read the current cask version")
    old = tuple(map(int, previous[1].split(".")))
    new = tuple(map(int, version.split(".")))
    if new < old:
        raise ValueError("Refusing a version downgrade")
    current_hash = re.search(r'^  sha256 "([a-f0-9]{64})"$', content, re.M)
    if not current_hash:
        raise ValueError("Cannot read the current cask checksum")
    if new == old and digest != current_hash[1]:
        raise ValueError("Refusing replacement of an existing version")
    content, count = re.subn(r'^  version "[^"\n]+"$', f'  version "{version}"', content, flags=re.M)
    if count != 1:
        raise ValueError("Expected one version stanza")
    content, count = re.subn(r'^  sha256 "[^"\n]+"$', f'  sha256 "{digest}"', content, flags=re.M)
    if count != 1:
        raise ValueError("Expected one checksum stanza")
    return content


def sync(token, config, check):
    release = json.loads(subprocess.run(
        ["gh", "api", f'repos/{config["repository"]}/releases/latest'],
        check=True, capture_output=True, text=True,
    ).stdout)
    tag = release.get("tag_name", "")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ValueError("Invalid release tag")
    prefix = f'https://github.com/{config["repository"]}/releases/download/{tag}/'
    manifest = json.loads(fetch(prefix + "release-manifest.json"))
    filename, prefix, digest, size = validate_release(config, release, manifest)
    content = (ROOT / "Casks" / (token + ".rb")).read_text()
    updated = update_cask(content, manifest["version"], digest)
    if check and updated != content:
        raise ValueError("Cask differs from the latest verified release")
    checksums = fetch(prefix + "SHA256SUMS").decode().splitlines()
    if f"{digest}  {filename}" not in checksums:
        raise ValueError("Checksum file mismatch")
    with tempfile.TemporaryDirectory() as directory:
        package = Path(directory) / filename
        data = fetch(prefix + filename)
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("Downloaded package integrity mismatch")
        package.write_bytes(data)
        subprocess.run([
            "gh", "attestation", "verify", str(package), "--repo", config["repository"],
            "--signer-workflow", config["repository"] + "/.github/workflows/" + config["workflows"][manifest["signing"]],
            "--source-digest", manifest["commit"], "--source-ref", "refs/tags/" + tag,
            "--deny-self-hosted-runners",
        ], check=True)
    if not check and updated != content:
        (ROOT / "Casks" / (token + ".rb")).write_text(updated)
    print(f'Verified {token} {manifest["version"]} ({manifest["signing"]})')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for token, config in json.loads((ROOT / "apps.json").read_text()).items():
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", token):
            raise ValueError("Invalid cask token")
        sync(token, config, args.check)


if __name__ == "__main__":
    main()
