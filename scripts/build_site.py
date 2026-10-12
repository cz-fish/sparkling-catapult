#!/usr/bin/env python3
"""Build the picture blog as a static site suitable for GitHub Pages."""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

import yaml


ROOT = Path(__file__).resolve().parent.parent
PAGE_SIZE = 12


@dataclass(frozen=True)
class Post:
    title: str
    picture: Path
    published: date
    series: str | None
    ordinal: int | None
    text: str

    @property
    def search_text(self) -> str:
        return f"{self.title} {self.text}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise ValueError(f"Cannot make a URL slug from {value!r}")
    return slug


def load_posts(posts_dir: Path, pictures_dir: Path) -> list[Post]:
    posts: list[Post] = []
    seen_slugs: set[str] = set()

    for metadata_path in sorted(posts_dir.glob("*.yaml")) + sorted(
        posts_dir.glob("*.yml")
    ):
        if metadata_path.stem in seen_slugs:
            raise ValueError(f"Duplicate post metadata filename: {metadata_path.stem}")
        seen_slugs.add(metadata_path.stem)

        with metadata_path.open(encoding="utf-8") as metadata_file:
            data = yaml.safe_load(metadata_file)
        if not isinstance(data, dict):
            raise ValueError(f"{metadata_path}: expected a YAML mapping")

        title = data.get("title")
        picture_value = data.get("picture")
        published_value = data.get("date")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{metadata_path}: 'title' must be a non-empty string")
        if not isinstance(picture_value, str) or not picture_value.strip():
            raise ValueError(f"{metadata_path}: 'picture' must be a non-empty path")
        if isinstance(published_value, datetime):
            published = published_value.date()
        elif isinstance(published_value, date):
            published = published_value
        elif isinstance(published_value, str):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published_value):
                raise ValueError(
                    f"{metadata_path}: 'date' must use YYYY-MM-DD format"
                )
            try:
                published = date.fromisoformat(published_value)
            except ValueError as error:
                raise ValueError(
                    f"{metadata_path}: 'date' must use YYYY-MM-DD format"
                ) from error
        else:
            raise ValueError(f"{metadata_path}: 'date' must use YYYY-MM-DD format")

        picture = Path(picture_value)
        if picture.is_absolute() or picture.drive or ".." in picture.parts:
            raise ValueError(f"{metadata_path}: 'picture' must stay inside pictures/")
        picture_source = pictures_dir / picture
        if not picture_source.is_file():
            raise ValueError(f"{metadata_path}: picture file not found: {picture_source}")
        if not picture_source.resolve().is_relative_to(pictures_dir.resolve()):
            raise ValueError(f"{metadata_path}: picture symlinks must stay in pictures/")

        series_value = data.get("series")
        if series_value is not None and (
            not isinstance(series_value, str) or not series_value.strip()
        ):
            raise ValueError(f"{metadata_path}: 'series' must be a non-empty string")
        ordinal_value = data.get("ordinal")
        if ordinal_value is not None and (
            not isinstance(ordinal_value, int)
            or isinstance(ordinal_value, bool)
            or ordinal_value < 1
        ):
            raise ValueError(f"{metadata_path}: 'ordinal' must be a positive integer")
        if (series_value is None) != (ordinal_value is None):
            raise ValueError(
                f"{metadata_path}: 'series' and 'ordinal' must be provided together"
            )

        text_value = data.get("text", "")
        if not isinstance(text_value, str):
            raise ValueError(f"{metadata_path}: 'text' must be a string")
        posts.append(
            Post(
                title=title.strip(),
                picture=picture,
                published=published,
                series=series_value.strip() if series_value else None,
                ordinal=ordinal_value,
                text=text_value.strip(),
            )
        )

    posts.sort(key=lambda post: (post.published, post.title.casefold()))
    validate_series(posts)
    return posts


def validate_series(posts: list[Post]) -> None:
    series_slugs: dict[str, str] = {}
    ordinals: set[tuple[str, int]] = set()
    for post in posts:
        if post.series is None or post.ordinal is None:
            continue
        series_slug = slugify(post.series)
        previous_name = series_slugs.setdefault(series_slug, post.series)
        if previous_name != post.series:
            raise ValueError(
                f"Series names {previous_name!r} and {post.series!r} "
                "produce the same URL"
            )
        key = (series_slug, post.ordinal)
        if key in ordinals:
            raise ValueError(
                f"Series {post.series!r} has duplicate ordinal {post.ordinal}"
            )
        ordinals.add(key)


def relative_url(path: Path) -> str:
    return quote(path.as_posix(), safe="/")


def render_post(post: Post, picture_url: str, prefix: str) -> str:
    title = html.escape(post.title)
    text = html.escape(post.text)
    search_text = html.escape(post.search_text, quote=True)
    story = ""
    if post.series is not None and post.ordinal is not None:
        story = (
            f' · <a href="{prefix}stories/{quote(slugify(post.series))}/index.html">'
            f"{html.escape(post.series)} #{post.ordinal}</a>"
        )
    description = f"<p>{text}</p>" if text else ""
    return f"""<article class="post" data-search-text="{search_text}" tabindex="0" aria-haspopup="dialog" aria-label="Open post: {title}">
  <img src="{picture_url}" alt="{title}" loading="lazy">
  <h2>{title}</h2>
  <p class="post-meta"><time datetime="{post.published.isoformat()}">{post.published.isoformat()}</time>{story}</p>
  {description}
</article>"""


def render_page(
    title: str,
    posts: list[Post],
    page_depth: int,
    series_links: list[tuple[str, str]],
    is_story: bool = False,
) -> str:
    prefix = "../" * page_depth
    nav = " ".join(
        f'<a href="{prefix}stories/{quote(slug)}/index.html">{html.escape(name)}</a>'
        for slug, name in series_links
    )
    if is_story:
        nav = f'<a href="{prefix}index.html">All posts</a> {nav}'

    cards: list[str] = []
    for post in posts:
        picture_url = prefix + "pictures/" + relative_url(post.picture)
        cards.append(render_post(post, picture_url, prefix))

    empty_state = (
        '<p class="empty-state" data-empty-for="posts" hidden>'
        "No posts match your search.</p>"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{prefix}assets/css/style.css">
  <script src="{prefix}assets/js/site.js" defer></script>
</head>
<body>
  <header class="page-header">
    <h1><a href="{prefix}index.html">Sparkling Catapult</a></h1>
    <p>{html.escape(title)}</p>
    <nav class="story-nav" aria-label="Stories">{nav}</nav>
  </header>
  <main>
    <section class="controls" aria-label="Browse posts">
      <label>Search titles and text
        <input type="search" data-search-for="posts">
      </label>
      <label>Order
        <select data-order-for="posts">
          <option value="newest">Newest first</option>
          <option value="oldest">Newest last</option>
        </select>
      </label>
    </section>
    <section id="posts" class="post-list" data-post-list data-page-size="{PAGE_SIZE}" aria-live="polite">
      {"".join(cards)}
    </section>
    {empty_state}
    <nav class="pagination" aria-label="Post pages">
      <button type="button" data-previous-for="posts">Previous</button>
      <span data-page-for="posts"></span>
      <button type="button" data-next-for="posts">Next</button>
    </nav>
  </main>
  <dialog class="post-viewer" aria-labelledby="viewer-title">
    <div class="viewer-toolbar">
      <button type="button" data-viewer-previous aria-label="Previous post">Previous</button>
      <button type="button" data-viewer-close aria-label="Close full-size post">Close</button>
      <button type="button" data-viewer-next aria-label="Next post">Next</button>
    </div>
    <img class="viewer-image" data-viewer-image alt="">
    <section class="viewer-details">
      <h2 id="viewer-title" data-viewer-title></h2>
      <div data-viewer-meta></div>
      <div data-viewer-text></div>
    </section>
  </dialog>
  <footer class="page-footer">Built from the blog's YAML posts.</footer>
</body>
</html>
"""


def build_site(posts_dir: Path, pictures_dir: Path, output_dir: Path) -> None:
    posts = load_posts(posts_dir, pictures_dir)
    series: dict[str, list[Post]] = {}
    names: dict[str, str] = {}
    for post in posts:
        if post.series is None:
            continue
        slug = slugify(post.series)
        series.setdefault(slug, []).append(post)
        names[slug] = post.series
    series_links = [(slug, names[slug]) for slug in sorted(series)]

    output_dir = output_dir.resolve()
    protected_paths = (
        posts_dir.resolve(),
        pictures_dir.resolve(),
        (ROOT / "assets").resolve(),
        (ROOT / "scripts").resolve(),
        (ROOT / ".git").resolve(),
        ROOT.resolve(),
    )
    if output_dir in protected_paths or any(
        path.is_relative_to(output_dir) for path in protected_paths
    ):
        raise ValueError(f"Refusing to replace a source directory: {output_dir}")
    if output_dir.exists():
        if not output_dir.is_dir():
            raise ValueError(f"Output path is not a directory: {output_dir}")
        marker = output_dir / ".pic-blog-generated"
        if not marker.is_file():
            raise ValueError(
                f"Refusing to replace a directory not generated by this script: "
                f"{output_dir}"
            )
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    (output_dir / ".pic-blog-generated").write_text(
        "Generated by scripts/build_site.py\n", encoding="utf-8"
    )

    shutil.copytree(ROOT / "assets", output_dir / "assets")
    shutil.copytree(pictures_dir, output_dir / "pictures")
    (output_dir / "index.html").write_text(
        render_page("All posts", posts, 0, series_links),
        encoding="utf-8",
    )
    stories_dir = output_dir / "stories"
    stories_dir.mkdir()
    for slug, story_posts in series.items():
        story_dir = stories_dir / slug
        story_dir.mkdir()
        story_posts.sort(
            key=lambda post: (post.published, post.ordinal or 0)
        )
        (story_dir / "index.html").write_text(
            render_page(
                names[slug],
                story_posts,
                2,
                series_links,
                is_story=True,
            ),
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--posts-dir", type=Path, default=ROOT / "content" / "posts")
    parser.add_argument(
        "--pictures-dir", type=Path, default=ROOT / "content" / "pictures"
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "site")
    args = parser.parse_args()

    try:
        build_site(args.posts_dir, args.pictures_dir, args.output_dir)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1
    print(f"Built static site in {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
