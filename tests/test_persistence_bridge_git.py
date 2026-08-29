import subprocess
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def test_force_with_lease_style_stale_head_refusal(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.check_call(["git", "init", "--bare", str(remote)], stdout=subprocess.DEVNULL)
    seed = tmp_path / "seed"
    subprocess.check_call(["git", "init", str(seed)], stdout=subprocess.DEVNULL)
    git(seed, "config", "user.email", "test@example.invalid")
    git(seed, "config", "user.name", "Test")
    (seed / "x.txt").write_text("base\n", encoding="utf-8")
    git(seed, "add", "x.txt")
    git(seed, "commit", "-m", "base")
    git(seed, "branch", "-M", "chapter/test/r001-001/g1")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-u", "origin", "chapter/test/r001-001/g1")
    expected = git(seed, "rev-parse", "HEAD")

    contender = tmp_path / "contender"
    subprocess.check_call(["git", "clone", str(remote), str(contender)], stdout=subprocess.DEVNULL)
    git(contender, "config", "user.email", "test@example.invalid")
    git(contender, "config", "user.name", "Test")
    git(contender, "checkout", "chapter/test/r001-001/g1")
    (contender / "x.txt").write_text("moved\n", encoding="utf-8")
    git(contender, "commit", "-am", "move remote")
    git(contender, "push", "origin", "HEAD:chapter/test/r001-001/g1")

    (seed / "y.txt").write_text("bridge\n", encoding="utf-8")
    git(seed, "add", "y.txt")
    git(seed, "commit", "-m", "bridge")
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(seed),
            "push",
            f"--force-with-lease=refs/heads/chapter/test/r001-001/g1:{expected}",
            "origin",
            "HEAD:refs/heads/chapter/test/r001-001/g1",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode != 0
    assert "stale info" in proc.stderr or "rejected" in proc.stderr
