# Jeremiah's Homebrew tap

Reusable public tap for apps and command-line tools published by Jeremiah Lusato.
Mac apps live in `Casks/`; add `Formula/` when the first command-line tool needs it.
This is a third-party tap maintained by Jeremiah, not the official Homebrew catalog.

## Install and update Mac Usage

Requires macOS 13+, Apple Silicon or Intel, and Homebrew:

```sh
brew install --cask jerrylusato/tap/mac-usage
brew update
brew upgrade --cask mac-usage
```

Use `brew upgrade --cask jerrylusato/tap/mac-usage` if another tap has the same name.
Homebrew downloads the published universal DMG and verifies its pinned SHA-256 checksum.
Quit Mac Usage before upgrading. An app previously copied into Applications manually
may conflict with installation; quit it and move that app bundle aside first. Its history
is stored separately in `~/Library/Application Support/MacUsageTracker` and is preserved.
Do not use `--force` to overwrite an unrelated installation.

**Mac Usage is ad-hoc signed and is not notarized by Apple.** After trying to open it,
use System Settings → Privacy & Security → Open Anyway for an unidentified-developer
block only if you trust the project/download. Managed Macs may prohibit this exception.
The cask does not disable Gatekeeper, remove quarantine, launch the app, or delete history.
Normal `brew uninstall --cask mac-usage` preserves history; there is intentionally no zap stanza.
Homebrew may request explicit trust for this cask; trust only the named cask when prompted.

## Release maintenance

`apps.json` lists the repositories, manifest identities, package filename patterns, and
trusted release workflow paths. `scripts/sync_releases.py` discovers the latest stable
public releases and validates their manifest, owned URLs, size, checksum file, downloaded
SHA-256, and GitHub-hosted build provenance for the exact source commit/tag and workflow.
It refuses downgrades or changes to an already published version. It changes only the
version and checksum stanzas; download/install instructions remain reviewed code.

`.github/workflows/refresh.yml` checks daily at 03:43 UTC / 06:43 EAT (GitHub schedules can
be delayed) or via **Run workflow**. When needed, it opens a PR, explicitly dispatches the
verification workflow on that branch, and enables auto-merge. This uses only the tap's
own ephemeral `GITHUB_TOKEN`; no cross-repository PAT or app signing key is needed.
Release API discovery uses authenticated `gh api` to avoid shared runner IP rate limits;
public asset downloads do not receive the token.
The tap's **Allow GitHub Actions to create and approve pull requests** setting and
repository auto-merge are enabled for unattended updates. The workflow creates PRs
but never approves reviews. Merged branches are deleted automatically. `main` requires
PRs, the `verify` check, an up-to-date branch, and resolved conversations; force pushes
and deletion are disabled. The solo owner can merge verified PRs without a second reviewer.

Verification runs unit tests, live release/provenance checks, Homebrew style/audit, and
installation/uninstallation into a temporary directory on a disposable macOS runner,
verifying the installed version, signature, and both architectures without launching it.
Successful Mac release publication is the source of truth; tap availability follows the
next refresh and successful checks. If verification fails, the existing cask stays in place.
Checksums and provenance do not certify malware safety or replace Apple notarization.

## Local checks and adding packages

```sh
python3 -m unittest discover -s tests -v
python3 scripts/sync_releases.py --check
brew style --cask jerrylusato/tap/mac-usage
brew audit --cask jerrylusato/tap/mac-usage
```

`gh` must be authenticated for provenance verification. To add an app, write and review
its cask, add its immutable release mapping to `apps.json`, extend the workflow's package
checks, and verify installation on the declared architectures/macOS versions. Formulae
need their own build/test checks and can reuse this repository without using the Mac
manifest updater. Published release assets and tags must never be overwritten.

MIT licensed. Source and download instructions: https://usage.jerrylusato.com.
