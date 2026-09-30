#!/usr/bin/env python3
# ruff: noqa: T201
"""验证脚本用到的辅助命令，只依赖标准库。凡是接触凭证的命令都只输出计数或状态码。"""

import base64
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter


def _host_of(key):
    parsed = urllib.parse.urlparse(key if "://" in key else "//" + key)
    return parsed.netloc or key


def _secrets(config_path):
    with open(config_path) as f:
        auths = json.load(f).get("auths", {})
    values = set()
    for entry in auths.values():
        for field in ("password", "auth", "identitytoken", "registrytoken"):
            if entry.get(field):
                values.add(entry[field])
        if entry.get("auth"):
            _, _, pwd = base64.b64decode(entry["auth"]).decode().partition(":")
            if pwd:
                values.add(pwd)
    return [v for v in values if len(v) >= 6]


def merge_configs(out, *paths):
    merged = {}
    for p in paths:
        with open(os.path.expanduser(p)) as f:
            for key, entry in json.load(f).get("auths", {}).items():
                merged[_host_of(key).lower()] = entry
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"auths": merged}, f)
    print(" ".join(sorted(merged)))


def claims(out, *args):
    """claims <输出文件> --sub S [--pull P]... [--pull-deny P]... [--push REPO=TAG[,TAG]]..."""
    c = {"sub": "", "app_code": "e2e", "module": "default", "push": [], "pull": [], "pull_deny": []}
    it = iter(args)
    for flag in it:
        value = next(it)
        if flag == "--sub":
            c["sub"] = value
        elif flag == "--pull":
            c["pull"].append(value)
        elif flag == "--pull-deny":
            c["pull_deny"].append(value)
        elif flag == "--push":
            repo, _, tags = value.partition("=")
            c["push"].append({"repo": repo, "tags": [t for t in tags.split(",") if t]})
        else:
            raise SystemExit(f"unknown flag {flag}")
    with open(out, "w") as f:
        json.dump(c, f)


def _read(path):
    with open(path, errors="replace") as f:
        return f.read()


def leak_hits(config_path, log_path):
    text = _read(log_path)
    print(sum(text.count(s) for s in _secrets(config_path)))


def count_in(needle_file, log_path):
    needle = _read(needle_file).strip()
    print(_read(log_path).count(needle))


def redact(config_path, *token_files):
    needles = _secrets(config_path) + [_read(t).strip() for t in token_files if os.path.exists(t)]
    for raw in sys.stdin:
        redacted = raw
        for n in needles:
            redacted = redacted.replace(n, "<redacted>")
        sys.stdout.write(redacted)


def audit_summary(audit_path, sub):
    rows = []
    with open(audit_path) as f:
        for line in f:
            e = json.loads(line)
            if e.get("sub") == sub:
                rows.append(e)
    if not rows:
        print("   （审计日志中没有该构建的记录）")
        return
    by_kind = Counter()
    bytes_in = Counter()
    bytes_out = Counter()
    redirects = Counter()
    statuses = Counter()
    denies = Counter()
    for e in rows:
        k = f"{e['method']} {e['route']}"
        by_kind[k] += 1
        bytes_in[k] += e["req_bytes"]
        bytes_out[k] += e["resp_bytes"]
        statuses[e["status"]] += 1
        if e.get("redirect_host"):
            redirects[e["redirect_host"]] += 1
        if e.get("deny"):
            denies[e["deny"]] += 1

    def mb(n):
        return f"{n / 1024 / 1024:.2f}MB" if n >= 1024 * 1024 else f"{n}B"

    print(f"   请求 {len(rows)} 次，状态码分布 {dict(sorted(statuses.items()))}")
    for k in sorted(by_kind):
        print(f"   {k:<20} {by_kind[k]:>4} 次  上行 {mb(bytes_in[k]):>10}  下行 {mb(bytes_out[k]):>10}")
    total_in = sum(bytes_in.values())
    total_out = sum(bytes_out.values())
    print(f"   经代理合计：上行 {mb(total_in)}，下行 {mb(total_out)}")
    if redirects:
        print(f"   307 透传给客户端直连：{dict(redirects)}")
    if denies:
        print(f"   被拒绝：{dict(denies)}")


def audit_count(audit_path, sub_prefix, field, value=None):
    """统计 sub 以 sub_prefix 开头、且 field 非空（或等于 value）的审计记录数"""
    n = 0
    with open(audit_path) as f:
        for line in f:
            e = json.loads(line)
            if not e.get("sub", "").startswith(sub_prefix):
                continue
            if (value is None and e.get(field)) or (value is not None and str(e.get(field)) == value):
                n += 1
    print(n)


def upstream_token_probe(host, repo, token_file, insecure=""):
    """拿构建 token 当作上游密码去换上游 token，再用换到的 token 尝试发起上传。

    输出形如 token-<换 token 状态码>/upload-<上传状态码>，只输出状态码。
    有的上游对无效凭证也会签发匿名级别的 token，因此关键看能否上传。
    """
    token = _read(token_file).strip()
    scheme = "http" if insecure == "1" else "https"
    ctx = ssl.create_default_context()
    basic = "Basic " + base64.b64encode(f"bkpaas-build:{token}".encode()).decode()

    def get(url, headers=None, method="GET"):
        if urllib.parse.urlparse(url).scheme not in ("http", "https"):
            raise ValueError(f"refusing URL scheme of {url}")
        req = urllib.request.Request(url, headers=headers or {}, method=method)  # noqa: S310
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:  # noqa: S310
                return resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    upload_url = f"{scheme}://{host}/v2/{repo}/blobs/uploads/"
    status, headers, _ = get(f"{scheme}://{host}/v2/")
    challenge = headers.get("WWW-Authenticate", "")
    if status == 200 or not challenge:
        print(f"anonymous-{status}")
        return
    if not challenge.lower().startswith("bearer"):
        status, _, _ = get(upload_url, {"Authorization": basic}, "POST")
        print(f"basic/upload-{status}")
        return

    params = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
    query = {"scope": f"repository:{repo}:pull,push"}
    if params.get("service"):
        query["service"] = params["service"]
    url = params["realm"] + ("&" if "?" in params["realm"] else "?") + urllib.parse.urlencode(query)
    status, _, body = get(url, {"Authorization": basic})
    if status != 200:
        print(f"token-{status}")
        return
    try:
        data = json.loads(body)
        upstream_token = data.get("token") or data.get("access_token")
    except ValueError:
        upstream_token = ""
    status, _, _ = get(upload_url, {"Authorization": f"Bearer {upstream_token}"}, "POST")
    print(f"token-200/upload-{status}")


COMMANDS = {
    "merge-configs": merge_configs,
    "claims": claims,
    "leak-hits": leak_hits,
    "count-in": count_in,
    "redact": redact,
    "audit-summary": audit_summary,
    "audit-count": audit_count,
    "upstream-token-probe": upstream_token_probe,
}

if __name__ == "__main__":
    COMMANDS[sys.argv[1]](*sys.argv[2:])
