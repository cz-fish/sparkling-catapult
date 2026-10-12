# Picture blog

This repository stores post metadata as YAML and source images under `content/`.
The build script generates a static site that can be published with GitHub Pages.

## Add a post

1. Put the image in `content/pictures/`.
2. Add a `.yaml` file in `content/posts/`:

   ```yaml
   title: First light
   picture: first-light.jpg
   date: 2026-10-09
   series: Sketchbook
   ordinal: 1
   text: A short caption for this picture.
   ```

   `series`, `ordinal`, and `text` are optional. If a post has a `series`, it
   must also have a positive integer `ordinal`. Dates use `YYYY-MM-DD`.
3. Install the Python dependency and rebuild:

   ```powershell
   py -m pip install -r requirements.txt
   py scripts\build_site.py
   ```

The generated site is written to `site/`. It contains the home page, one page
per story, styles, scripts, and the referenced pictures. Search checks titles
and captions; order and pagination work in the browser without a server. Click
a post (or focus it and press Enter/Space) to open its full-size image. The
overlay's Previous and Next controls follow the current search and sort order,
including across pages. Close it with the Close button, Escape, or by clicking
the backdrop.

## Publish to GitHub Pages

Build the site, then create a local commit on `gh-pages`:

```powershell
py scripts\build_site.py
py scripts\publish_site.py
```

The publisher replaces the previous contents of `gh-pages` with `site/` and
commits the result without pushing. It uses a temporary detached Git worktree,
so your current branch and uncommitted changes remain untouched. The
branch is created if it does not yet exist. The `.pic-blog-generated` safety
marker is not included in the published site. Push `gh-pages` separately when
you are ready to publish.
