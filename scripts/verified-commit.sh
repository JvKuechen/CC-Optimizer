#!/bin/bash
# verified-commit.sh -- Commit wrapper for public repos.
#
# The pre-commit hook blocks direct `git commit` when .public-repo exists.
# This script sets the bypass flag and passes all arguments to git commit.
#
# Usage:
#   scripts/verified-commit.sh -m "Add health check standard"
#   scripts/verified-commit.sh    (opens editor for message)
#
# The caller (Claude or human) is asserting they have reviewed the staged
# diff and confirmed it contains only generalized, non-sensitive content.

export PUBLIC_REPO_VERIFIED=1
exec git commit "$@"
