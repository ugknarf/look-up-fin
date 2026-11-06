#!/usr/bin/env python3
"""Push, pull, list and publish the shop.lookupfin.com theme in shopify/.

Same credentials as tools/shopify.py (~/.config/lookupfin/shopify.env).

    python3 tools/theme.py list                  # themes in the store, with preview links
    python3 tools/theme.py push [NAME]           # upload shopify/ as unpublished theme NAME
                                                 #   (default: the current git branch)
    python3 tools/theme.py pull NAME             # bring NAME's files back into shopify/
    python3 tools/theme.py publish NAME          # make NAME the live theme

Variants are git branches: branch, edit shopify/, `push`, open the preview link.
Push again with the same name to replace it. Emily's edits in Customize land on
that theme in Shopify; `pull` brings them into git.
"""
import base64
import json
import mimetypes
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from shopify import gql, check_user_errors, load_env  # noqa: E402

THEME_DIR = Path(__file__).resolve().parent.parent / "shopify"
SKIP = {"README.md", ".gitignore", ".DS_Store"}


def themes():
    d = gql("query { themes(first: 50) { nodes { id name role updatedAt } } }")
    return d["themes"]["nodes"]


def find(name):
    for t in themes():
        if t["name"] == name:
            return t
    return None


def preview_url(theme_id):
    store, _ = load_env()
    tid = theme_id.rsplit("/", 1)[1]
    return f"https://shop.lookupfin.com/?preview_theme_id={tid}"


def local_files():
    for p in sorted(THEME_DIR.rglob("*")):
        if p.is_file() and p.name not in SKIP:
            yield p.relative_to(THEME_DIR).as_posix(), p


def is_text(path):
    t, _ = mimetypes.guess_type(path)
    return path.endswith((".liquid", ".json", ".css", ".js", ".svg", ".md", ".txt")) or (t and t.startswith("text/"))


def cmd_list(_):
    for t in themes():
        print(f"{t['role']:<12} {t['name']:<24} {t['updatedAt'][:16]}  {preview_url(t['id']) if t['role'] != 'MAIN' else 'https://shop.lookupfin.com/'}")


def cmd_push(args):
    name = args[0] if args else git_branch()
    t = find(name)
    if not t:
        create_empty(name)
    files = []
    for rel, p in local_files():
        if is_text(rel):
            files.append({"filename": rel, "body": {"type": "TEXT", "value": p.read_text()}})
        else:
            files.append({"filename": rel, "body": {"type": "BASE64", "value": base64.b64encode(p.read_bytes()).decode()}})
    for i in range(0, len(files), 50):  # API cap per call
        d = gql("""mutation($id: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
                  themeFilesUpsert(themeId: $id, files: $files) {
                    upsertedThemeFiles { filename } userErrors { filename message } } }""",
                {"id": t["id"], "files": files[i:i + 50]})
        check_user_errors(d, "themeFilesUpsert")
    print(f"pushed {len(files)} files to '{name}' ({t['role']})\npreview: {preview_url(t['id'])}")


def create_empty(name):
    # themeCreate needs a public zip URL, so the first upload of a new name is manual.
    sys.exit(f"No theme named '{name}' in the store yet. Create it once by uploading a zip\n"
             f"(Online Store > Themes > Import > Upload zip file) named '{name}', then push again.")


def cmd_pull(args):
    if not args:
        sys.exit("usage: pull NAME")
    t = find(args[0])
    if not t:
        sys.exit(f"no theme named {args[0]}")
    d = gql("""query($id: ID!) { theme(id: $id) { files(first: 250) { nodes {
              filename body { ... on OnlineStoreThemeFileBodyText { content }
                              ... on OnlineStoreThemeFileBodyBase64 { contentBase64 } } } } } }""",
            {"id": t["id"]})
    n = 0
    for f in d["theme"]["files"]["nodes"]:
        p = THEME_DIR / f["filename"]
        p.parent.mkdir(parents=True, exist_ok=True)
        b = f["body"]
        if "content" in b:
            p.write_text(b["content"])
        else:
            p.write_bytes(base64.b64decode(b["contentBase64"]))
        n += 1
    print(f"pulled {n} files from '{args[0]}' into shopify/. Review with git diff.")


def cmd_publish(args):
    if not args:
        sys.exit("usage: publish NAME")
    t = find(args[0])
    if not t:
        sys.exit(f"no theme named {args[0]}")
    d = gql("""mutation($id: ID!) { themePublish(id: $id) { theme { name role } userErrors { message } } }""",
            {"id": t["id"]})
    check_user_errors(d, "themePublish")
    print(f"'{args[0]}' is live at https://shop.lookupfin.com/")


def git_branch():
    import subprocess
    return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip() or "main"


COMMANDS = {"list": cmd_list, "push": cmd_push, "pull": cmd_pull, "publish": cmd_publish}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
