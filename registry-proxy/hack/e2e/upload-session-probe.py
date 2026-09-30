#!/usr/bin/env python3
# ruff: noqa: T201
"""直连上游，验证上游自身对 blob 上传会话的约束，用于评估代理是否需要自行签名上传会话。

    upload-session-probe.py <docker config> <上游主机> <仓库 A> <仓库 B>

A、B 都应是推送账号有权限的测试仓库。脚本用代理持有的上游凭证（与代理的换 token 方式一致）依次检查：

  1. 开始上传时上游返回的 Location 格式；
  2. 对照：在 A 下正常续传、完成上传；
  3. 把 A 的上传会话拿到 B 的路径下续传、完成上传；
  4. 伪造上传 ID、去掉 _state、篡改 _state 时的上游响应。

只输出状态码与地址结构，不输出凭证与 token。
"""

import base64
import hashlib
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

CTX = ssl.create_default_context()


def request(method, url, headers=None, body=None):
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        raise ValueError(f"refusing URL scheme of {url}")
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


urllib.request.install_opener(urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=CTX)))


def credential(config_path, host):
    with open(config_path) as f:
        auths = json.load(f)["auths"]
    entry = auths[host]
    if entry.get("username"):
        return entry["username"], entry["password"]
    user, _, pwd = base64.b64decode(entry["auth"]).decode().partition(":")
    return user, pwd


def authorization(base, user, pwd, repos):
    status, headers, _ = request("GET", base + "/v2/")
    challenge = headers.get("WWW-Authenticate", "")
    basic = "Basic " + base64.b64encode(f"{user}:{pwd}".encode()).decode()
    if status == 200 or challenge.lower().startswith("basic"):
        return basic
    params = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
    query = [("service", params.get("service", ""))] + [("scope", f"repository:{r}:pull,push") for r in repos]
    url = params["realm"] + ("&" if "?" in params["realm"] else "?") + urllib.parse.urlencode(query)
    status, _, body = request("GET", url, {"Authorization": basic})
    if status != 200:
        raise SystemExit(f"换取上游 token 失败：{status}")
    data = json.loads(body)
    return "Bearer " + (data.get("token") or data.get("access_token"))


def describe_location(base, repo, loc):
    """描述 Location 的结构，不输出 _state 的内容"""
    u = urllib.parse.urlparse(urllib.parse.urljoin(base + "/", loc))
    host = "同一主机" if u.netloc == urllib.parse.urlparse(base).netloc else f"其他主机 {u.netloc}"
    std = re.fullmatch(rf"/v2/{re.escape(repo)}/blobs/uploads/[^/]+", u.path) is not None
    keys = sorted(urllib.parse.parse_qs(u.query).keys())
    shape = re.sub(r"/blobs/uploads/[^/]+$", "/blobs/uploads/<id>", u.path)
    return f"{host}，路径 {shape}（{'标准格式' if std else '非标准格式'}），查询参数 {keys or '无'}"


def start(base, auth, repo):
    status, headers, _ = request(
        "POST", f"{base}/v2/{repo}/blobs/uploads/", {"Authorization": auth, "Content-Length": "0"}
    )
    loc = headers.get("Location", "")
    return status, urllib.parse.urljoin(base + "/", loc) if loc else ""


def swap_repo(loc, repo_a, repo_b):
    u = urllib.parse.urlparse(loc)
    return u._replace(path=u.path.replace(f"/v2/{repo_a}/", f"/v2/{repo_b}/", 1)).geturl()


def with_query(loc, **kw):
    u = urllib.parse.urlparse(loc)
    q = urllib.parse.parse_qsl(u.query)
    q = [(k, v) for k, v in q if k not in kw] + [(k, v) for k, v in kw.items() if v is not None]
    return u._replace(query=urllib.parse.urlencode(q)).geturl()


def patch(auth, loc, data):
    status, headers, _ = request(
        "PATCH",
        loc,
        {
            "Authorization": auth,
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(data)),
            "Content-Range": f"0-{len(data) - 1}",
        },
        data,
    )
    return status, headers.get("Location", "")


def put(auth, loc, digest):
    status, headers, _ = request("PUT", with_query(loc, digest=digest), {"Authorization": auth, "Content-Length": "0"})
    return status, headers.get("Location", "")


def head_blob(base, auth, repo, digest):
    status, _, _ = request("HEAD", f"{base}/v2/{repo}/blobs/{digest}", {"Authorization": auth})
    return status


def blob():
    data = os.urandom(1024)
    return data, "sha256:" + hashlib.sha256(data).hexdigest()


def main():
    config, host, repo_a, repo_b = sys.argv[1:5]
    base = "https://" + host
    user, pwd = credential(config, host)
    auth = authorization(base, user, pwd, [repo_a, repo_b])
    print(f"== {host}：A={repo_a}，B={repo_b}")

    status, loc = start(base, auth, repo_a)
    print(f"1. 开始上传：{status}，Location：{describe_location(base, repo_a, loc)}")
    if status != 202:
        return

    data, digest = blob()
    s1, loc2 = patch(auth, loc, data)
    s2, _ = put(auth, urllib.parse.urljoin(base + "/", loc2) if loc2 else loc, digest)
    print(f"2. 对照：A 下续传 {s1}，完成 {s2}，A 中 blob {head_blob(base, auth, repo_a, digest)}")

    _, loc = start(base, auth, repo_a)
    data, digest = blob()
    s1, loc2 = patch(auth, swap_repo(loc, repo_a, repo_b), data)
    next_loc = urllib.parse.urljoin(base + "/", loc2) if loc2 else swap_repo(loc, repo_a, repo_b)
    s2, _ = put(auth, swap_repo(next_loc, repo_a, repo_b), digest)
    print(
        f"3. A 的会话拿到 B 路径下：续传 {s1}，完成 {s2}；"
        f"blob 在 A {head_blob(base, auth, repo_a, digest)}，在 B {head_blob(base, auth, repo_b, digest)}"
    )

    _, loc = start(base, auth, repo_a)
    data, _ = blob()
    forged = re.sub(r"/blobs/uploads/[^/?]+", "/blobs/uploads/00000000-0000-4000-8000-000000000000", loc)
    print(f"4. 伪造上传 ID：续传 {patch(auth, forged, data)[0]}")
    print(f"5. 去掉 _state：续传 {patch(auth, with_query(loc, _state=None), data)[0]}")
    print(f"6. 篡改 _state：续传 {patch(auth, with_query(loc, _state='AAAA'), data)[0]}")


if __name__ == "__main__":
    main()
