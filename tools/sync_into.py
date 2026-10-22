# -*- coding: utf-8 -*-
"""把共享模块 `cbeta_fetch.py` 同步到宿主项目的 vendor 目录，并写 `SOURCE.txt`。

用法：
    python tools/sync_into.py <vendor_dir> [--from <cbeta_fetch.py 路径>]

`SOURCE.txt` 记录：repo / commit / version / sha256（宿主测试据此防手改）。
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.join(os.path.dirname(HERE), "cbeta_fetch.py")
REPO = "https://github.com/Zen-Bear/cbeta-fetch"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def version(path):
    import ast
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", "") == "__version__" for t in node.targets):
            return ast.literal_eval(node.value)
    return ""


def git_commit(path):
    try:
        out = subprocess.run(
            ["git", "-C", os.path.dirname(path), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False)
        return (out.stdout or "").strip() or "-"
    except Exception:  # noqa: BLE001
        return "-"


def main(argv=None):
    ap = argparse.ArgumentParser(description="vendor 同步 cbeta_fetch.py")
    ap.add_argument("vendor_dir", help="宿主项目的 vendor 目录")
    ap.add_argument("--from", dest="src", default=MODULE,
                    help="源 cbeta_fetch.py（默认本仓库）")
    ns = ap.parse_args(argv)

    src = os.path.abspath(ns.src)
    if not os.path.isfile(src):
        print(f"源不存在：{src}")
        return 1
    dest_dir = os.path.abspath(ns.vendor_dir)
    os.makedirs(dest_dir, exist_ok=True)
    dst = os.path.join(dest_dir, "cbeta_fetch.py")
    shutil.copyfile(src, dst)
    init = os.path.join(dest_dir, "__init__.py")
    if not os.path.isfile(init):
        open(init, "w", encoding="utf-8").close()
    with open(os.path.join(dest_dir, "SOURCE.txt"), "w", encoding="utf-8") as f:
        f.write(f"repo={REPO}\n")
        f.write(f"commit={git_commit(src)}\n")
        f.write(f"version={version(src)}\n")
        f.write(f"sha256={sha256(dst)}\n")
    print(f"synced -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
