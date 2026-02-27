"""Generate a push review for public repos.

Outputs a markdown-formatted consolidated diff comparing HEAD to the
remote tracking branch. Used by the push-review hook to present a
squash-style diff before pushing.

Usage: python scripts/push-review.py [remote]
"""
import subprocess
import sys


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return result.stdout.strip()


def main():
    remote = sys.argv[1] if len(sys.argv) > 1 else None

    # Auto-detect remote if not specified
    if not remote:
        remotes = run("git remote").splitlines()
        if "public" in remotes:
            remote = "public"
        elif remotes:
            remote = remotes[0]
        else:
            print("No remotes configured.")
            return

    branch = run("git symbolic-ref --short HEAD") or "main"
    remote_ref = "{}/{}".format(remote, branch)

    # Check if remote ref exists
    result = subprocess.run(
        "git rev-parse {}".format(remote_ref),
        capture_output=True, text=True, shell=True,
    )
    if result.returncode != 0:
        print("No remote ref {} found (first push?).".format(remote_ref))
        return

    # Commit count
    count = run("git rev-list --count {}..HEAD".format(remote_ref))
    if count == "0":
        print("Nothing to push -- up to date with remote.")
        return

    # Commit list
    commits = run("git log --oneline {}..HEAD".format(remote_ref))

    # Consolidated diff (net change, as if squashed)
    diff = run("git diff {}..HEAD".format(remote_ref))

    # Stat summary
    stat = run("git diff --stat {}..HEAD".format(remote_ref))

    # Output markdown
    print("### Push Review: `{}`\n".format(remote_ref))
    print("**{} commit(s):**".format(count))
    for line in commits.splitlines():
        idx = line.index(" ")
        print("- `{}` {}".format(line[:idx], line[idx + 1:]))
    print()
    print("**Summary:**")
    print("```")
    print(stat)
    print("```")
    print()
    print("**Consolidated diff:**")
    print("```diff")
    print(diff)
    print("```")
    print()
    print("Push with: `! git push {} {}`".format(remote, branch))


if __name__ == "__main__":
    main()
