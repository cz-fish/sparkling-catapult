from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.publish_site import PublishError, publish_site


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout.strip()


class PublishSiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        run_git(self.root, "init", "--quiet", "-b", "main")
        run_git(self.root, "config", "user.name", "Test User")
        run_git(self.root, "config", "user.email", "test@example.invalid")
        (self.root / "source.txt").write_text("source", encoding="utf-8")
        run_git(self.root, "add", "source.txt")
        run_git(self.root, "commit", "--quiet", "-m", "Initial source commit")
        self.main_commit = run_git(self.root, "rev-parse", "HEAD")
        run_git(self.root, "branch", "gh-pages")
        run_git(self.root, "switch", "--quiet", "gh-pages")
        (self.root / "old.txt").write_text("old site", encoding="utf-8")
        run_git(self.root, "add", "old.txt")
        run_git(self.root, "commit", "--quiet", "-m", "Old published site")
        self.old_pages_commit = run_git(self.root, "rev-parse", "HEAD")
        run_git(self.root, "switch", "--quiet", "main")

        self.site_dir = self.root / "site"
        self.site_dir.mkdir()
        (self.site_dir / ".pic-blog-generated").write_text(
            "Generated\n", encoding="utf-8"
        )
        (self.site_dir / "index.html").write_text(
            "<h1>New site</h1>", encoding="utf-8"
        )
        (self.site_dir / "assets").mkdir()
        (self.site_dir / "assets" / "style.css").write_text(
            "body {}", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_replaces_pages_contents_commits_and_preserves_current_worktree(self) -> None:
        dirty_file = self.root / "uncommitted.txt"
        dirty_file.write_text("keep me", encoding="utf-8")
        commit = publish_site(self.root, self.site_dir, "Publish test site")

        self.assertEqual(run_git(self.root, "branch", "--show-current"), "main")
        self.assertEqual(run_git(self.root, "rev-parse", "HEAD"), self.main_commit)
        self.assertEqual(dirty_file.read_text(encoding="utf-8"), "keep me")
        self.assertEqual(run_git(self.root, "rev-parse", "gh-pages"), commit)
        self.assertEqual(
            run_git(self.root, "rev-parse", "gh-pages^"), self.old_pages_commit
        )

        published = subprocess.run(
            ["git", "-C", str(self.root), "show", "gh-pages:index.html"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
        self.assertEqual(published, "<h1>New site</h1>")
        self.assertFalse((self.root / "old.txt").exists())
        self.assertEqual(
            run_git(self.root, "ls-tree", "-r", "--name-only", "gh-pages"),
            "assets/style.css\nindex.html",
        )

    def test_refuses_site_without_generator_marker(self) -> None:
        (self.site_dir / ".pic-blog-generated").unlink()

        with self.assertRaisesRegex(PublishError, "missing .pic-blog-generated"):
            publish_site(self.root, self.site_dir, "Publish test site")

        self.assertEqual(run_git(self.root, "branch", "--show-current"), "main")
        self.assertEqual(run_git(self.root, "rev-parse", "gh-pages"), self.old_pages_commit)

    def test_creates_gh_pages_as_a_root_commit_when_branch_is_missing(self) -> None:
        run_git(self.root, "branch", "--delete", "--force", "gh-pages")

        commit = publish_site(self.root, self.site_dir, "Initial site")

        self.assertEqual(run_git(self.root, "branch", "--show-current"), "main")
        self.assertEqual(run_git(self.root, "rev-parse", "gh-pages"), commit)
        self.assertEqual(
            run_git(self.root, "rev-list", "--parents", "-n", "1", "gh-pages"),
            commit,
        )


if __name__ == "__main__":
    unittest.main()
