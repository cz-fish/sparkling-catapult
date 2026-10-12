#!/usr/bin/env python3
"""Commit the generated site/ contents to the local gh-pages branch."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BRANCH = "gh-pages"
GENERATOR_MARKER = ".pic-blog-generated"


class PublishError(RuntimeError):
    """Raised when the site cannot safely be published."""


def git(root: Path, *args: str, input_text: str | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        input=input_text,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PublishError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def checked_out_branch(root: Path, branch: str) -> bool:
    worktrees = git(root, "worktree", "list", "--porcelain")
    expected = f"branch refs/heads/{branch}"
    return any(expected in block.splitlines() for block in worktrees.split("\n\n"))


def validate_site(site_dir: Path, repository: Path) -> Path:
    if site_dir.is_symlink() or not site_dir.is_dir():
        raise PublishError(f"Site directory does not exist or is a symlink: {site_dir}")

    resolved_site = site_dir.resolve()
    git_metadata = Path(git(repository, "rev-parse", "--absolute-git-dir")).resolve()
    if resolved_site == repository or resolved_site.is_relative_to(git_metadata):
        raise PublishError("The site directory cannot be the repository root or .git.")
    if not (resolved_site / GENERATOR_MARKER).is_file():
        raise PublishError(
            f"{resolved_site} is missing {GENERATOR_MARKER}; build it with "
            "scripts/build_site.py first."
        )
    if not (resolved_site / "index.html").is_file():
        raise PublishError(f"{resolved_site} is missing index.html.")

    for path in resolved_site.rglob("*"):
        if path.is_symlink():
            raise PublishError(f"Site contains a symbolic link: {path}")
        if path.name.casefold() == ".git":
            raise PublishError(f"Site contains a reserved .git path: {path}")
    return resolved_site


def clear_worktree(worktree: Path) -> None:
    for path in worktree.iterdir():
        if path.name == ".git":
            continue
        if path.is_symlink() or not path.is_dir():
            path.unlink()
        else:
            shutil.rmtree(path)


def copy_site(site_dir: Path, worktree: Path) -> None:
    for source in site_dir.iterdir():
        if source.name == GENERATOR_MARKER:
            continue
        destination = worktree / source.name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def publish_site(repository: Path, site_dir: Path, message: str) -> str:
    repository = Path(git(repository, "rev-parse", "--show-toplevel")).resolve()
    original_branch = git(repository, "branch", "--show-current")
    if not original_branch:
        raise PublishError("Run the publisher from a named branch, not detached HEAD.")

    resolved_site = validate_site(site_dir, repository)
    if checked_out_branch(repository, BRANCH):
        raise PublishError(
            f"The {BRANCH} branch is already checked out in a Git worktree."
        )

    old_target = git(
        repository, "for-each-ref", "--format=%(objectname)", f"refs/heads/{BRANCH}"
    )
    if not old_target:
        old_target = None
    base_commit = old_target or git(repository, "rev-parse", "HEAD")

    temporary_directory = tempfile.TemporaryDirectory(prefix="pic-blog-gh-pages-")
    worktree = Path(temporary_directory.name) / "worktree"
    worktree_added = False
    try:
        git(repository, "worktree", "add", "--detach", "--quiet", str(worktree), base_commit)
        worktree_added = True

        clear_worktree(worktree)
        copy_site(resolved_site, worktree)
        git(worktree, "add", "--force", "--all", "--", ".")
        tree = git(worktree, "write-tree")
        commit_args = ["commit-tree", tree, "-m", message]
        if old_target is not None:
            commit_args.extend(["-p", old_target])
        new_commit = git(repository, *commit_args)

        object_format = git(repository, "rev-parse", "--show-object-format")
        missing_object = "0" * (64 if object_format == "sha256" else 40)
        expected_old = old_target or missing_object
        git(
            repository,
            "update-ref",
            f"refs/heads/{BRANCH}",
            new_commit,
            expected_old,
        )
    finally:
        try:
            if worktree_added:
                git(repository, "worktree", "remove", "--force", str(worktree))
        finally:
            temporary_directory.cleanup()

    final_branch = git(repository, "branch", "--show-current")
    if final_branch != original_branch:
        raise PublishError(
            f"Current branch changed unexpectedly from {original_branch} to "
            f"{final_branch}."
        )
    return new_commit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=ROOT / "site")
    parser.add_argument(
        "--message",
        default=f"Publish site {datetime.now().astimezone():%Y-%m-%d %H:%M %Z}",
        help="Git commit message for the published site.",
    )
    args = parser.parse_args()

    try:
        commit = publish_site(ROOT, args.site_dir, args.message)
    except (OSError, PublishError) as error:
        print(f"Publish failed: {error}", file=sys.stderr)
        return 1
    print(f"Committed site to {BRANCH} as {commit}; no push was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
