import subprocess

from khipu import paths


def test_no_raw_data_committed():
    out = subprocess.run(
        ["git", "-C", str(paths.ROOT), "ls-files", "data/raw"], capture_output=True, text=True
    ).stdout.split()
    assert set(out) <= {"data/raw/MANIFEST.csv", "data/raw/.gitkeep"}
