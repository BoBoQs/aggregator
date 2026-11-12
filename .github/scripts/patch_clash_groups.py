# -*- coding: utf-8 -*-
"""Append a manual select group to the clash.yaml pushed to the Gist by Process.

Why this exists: the workflow runs subconverter with list_only=true, so the
pushed clash.yaml contains ONLY the proxies list (no proxy-groups, no rules).
FlClash shows no node page for such a file. This step adds ONE manual select
group ("节点选择") holding every node, plus a MATCH rule pointing at it.
No url-test, no fallback, nothing automatic - nodes are picked by hand.

Runs inside the Process workflow, right after the Process step. Needs:
  GIST_PAT - a token with gist scope (secrets.GIST_PAT)
  GIST_ID  - the gist id holding clash.yaml
Idempotent: exits 0 without changes if proxy-groups are already present.
"""
import json
import os
import re
import sys
import urllib.request

GIST_ID = os.environ.get("GIST_ID", "095f6060dc8932ec6ab409cc8f2e1cf5")
TOKEN = os.environ.get("GIST_PAT", "")
FILE = "clash.yaml"
GROUP_NAME = "节点选择"


def gh(method, url, data=None):
    req = urllib.request.Request(
        url,
        method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers={
            "Authorization": "token " + TOKEN,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    if not TOKEN:
        print("GIST_PAT missing, abort")
        return 1
    gist = gh("GET", "https://api.github.com/gists/" + GIST_ID)
    content = gist["files"][FILE]["content"]
    names = re.findall(r"^  - \{name: (.+?), server:", content, re.M)
    print("found %d proxies in %s" % (len(names), FILE))
    if not names:
        print("no proxies found, abort")
        return 1
    if "proxy-groups:" in content:
        print("proxy-groups already present, nothing to do")
        return 0
    lines = ["", "proxy-groups:", "  - name: " + GROUP_NAME, "    type: select", "    proxies:"]
    for n in names:
        q = '"' + n.replace("\\", "\\\\").replace('"', '\\"') + '"'
        lines.append("      - " + q)
    lines += ["", "rules:", "  - MATCH," + GROUP_NAME, ""]
    new_content = content.rstrip("\n") + "\n" + "\n".join(lines)
    gh("PATCH", "https://api.github.com/gists/" + GIST_ID,
       {"files": {FILE: {"content": new_content}}})
    print("patched %s: group %s with %d nodes" % (FILE, GROUP_NAME, len(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
