import copy
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("sync", Path(__file__).parents[1] / "scripts/sync_releases.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class ReleaseValidation(unittest.TestCase):
    def setUp(self):
        self.config = {"app": "mac", "repository": "jerrylusato/mac-usage-tracker",
                       "filename": "mac-usage-{version}-universal.dmg",
                       "workflows": {"ad-hoc": "release-adhoc.yml", "developer-id": "release.yml"}}
        self.filename = "mac-usage-1.0.0-universal.dmg"
        prefix = "https://github.com/jerrylusato/mac-usage-tracker/releases/download/v1.0.0/"
        self.release = {"tag_name": "v1.0.0", "draft": False, "prerelease": False,
                        "assets": [{"name": n, "browser_download_url": prefix + n, "size": 100}
                                   for n in (self.filename, "SHA256SUMS", "release-manifest.json")]}
        self.manifest = {"app": "mac", "version": "1.0.0", "tag": "v1.0.0", "build": 1,
                         "commit": "b" * 40, "signing": "ad-hoc", "notarized": False,
                         "files": [{"name": self.filename, "size": 100, "sha256": "a" * 64}]}
        self.cask = 'cask "sample" do\n  version "1.0.0"\n  sha256 "' + "a" * 64 + '"\nend\n'

    def test_accepts_both_signing_modes(self):
        for signing, notarized in (("ad-hoc", False), ("developer-id", True)):
            self.manifest.update(signing=signing, notarized=notarized)
            self.assertEqual(sync.validate_release(self.config, self.release, self.manifest)[0], self.filename)

    def test_rejects_unpublished_or_mismatched_release(self):
        for key, value in (("draft", True), ("prerelease", True), ("tag_name", "v9.9.9")):
            release = copy.deepcopy(self.release)
            release[key] = value
            with self.assertRaises(ValueError):
                sync.validate_release(self.config, release, self.manifest)

    def test_rejects_wrong_destination_or_digest(self):
        for key, value in (("browser_download_url", "https://example.com/app.dmg"), ("digest", "sha256:" + "c" * 64)):
            release = copy.deepcopy(self.release)
            release["assets"][0][key] = value
            with self.assertRaises(ValueError):
                sync.validate_release(self.config, release, self.manifest)

    def test_rejects_bad_manifest_identity_or_signing(self):
        for key, value in (("app", "phone"), ("build", True), ("commit", "main"),
                           ("notarized", True), ("signing", None)):
            manifest = copy.deepcopy(self.manifest)
            manifest[key] = value
            with self.assertRaises(ValueError):
                sync.validate_release(self.config, self.release, manifest)

    def test_refuses_downgrades_and_replaced_versions(self):
        for version, digest in (("0.9.0", "a" * 64), ("1.0.0", "b" * 64)):
            with self.assertRaises(ValueError):
                sync.update_cask(self.cask, version, digest)

    def test_changes_only_version_and_checksum(self):
        self.assertEqual(sync.update_cask(self.cask, "1.0.1", "c" * 64),
                         self.cask.replace('"1.0.0"', '"1.0.1"').replace("a" * 64, "c" * 64))
        self.assertEqual(sync.update_cask(self.cask, "1.0.0", "a" * 64), self.cask)


if __name__ == "__main__":
    unittest.main()
