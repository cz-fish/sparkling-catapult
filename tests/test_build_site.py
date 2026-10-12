from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_site import build_site


class BuildSiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.posts_dir = self.root / "posts"
        self.pictures_dir = self.root / "pictures"
        self.output_dir = self.root / "site"
        self.posts_dir.mkdir()
        self.pictures_dir.mkdir()
        (self.pictures_dir / "evening.jpg").write_bytes(b"image")
        (self.posts_dir / "evening.yaml").write_text(
            """title: "Evening & stars"
picture: evening.jpg
date: 2026-02-04
series: Night Walks
ordinal: 2
text: "A clear sky"
""",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_builds_home_story_and_assets_with_valid_relative_links(self) -> None:
        build_site(self.posts_dir, self.pictures_dir, self.output_dir)

        home = (self.output_dir / "index.html").read_text(encoding="utf-8")
        story = (
            self.output_dir / "stories" / "night-walks" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("Evening &amp; stars", home)
        self.assertIn("data-search-text=", home)
        self.assertIn('src="pictures/evening.jpg"', home)
        self.assertIn('href="stories/night-walks/index.html"', home)
        self.assertIn('aria-haspopup="dialog"', home)
        self.assertIn('<dialog class="post-viewer"', home)
        self.assertIn("data-viewer-previous", home)
        self.assertIn("data-viewer-next", home)
        self.assertIn("data-viewer-close", home)
        self.assertIn('href="../../stories/night-walks/index.html"', story)
        self.assertIn('href="../../index.html">All posts', story)
        self.assertTrue((self.output_dir / "pictures" / "evening.jpg").is_file())
        self.assertTrue((self.output_dir / "assets" / "js" / "site.js").is_file())

    def test_refuses_to_replace_directory_without_generator_marker(self) -> None:
        self.output_dir.mkdir()
        protected_file = self.output_dir / "keep.txt"
        protected_file.write_text("important", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "not generated"):
            build_site(self.posts_dir, self.pictures_dir, self.output_dir)

        self.assertEqual(protected_file.read_text(encoding="utf-8"), "important")

    def test_rejects_picture_paths_outside_picture_directory(self) -> None:
        (self.posts_dir / "evening.yaml").write_text(
            """title: Escape
picture: ../outside.jpg
date: 2026-02-04
""",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "stay inside pictures"):
            build_site(self.posts_dir, self.pictures_dir, self.output_dir)


if __name__ == "__main__":
    unittest.main()
