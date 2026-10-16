#!/usr/bin/env python3
# ruff: noqa: T201
"""直连上游，验证上游对 token scope 的处理：质询中返回的 scope，以及 token 是否按 scope 限制权限。

    scope-probe.py <docker config> <上游主机> <仓库 A> <A 中已存在的 tag> <仓库 B>

A、B 都应是推送账号有权限的测试仓库。写操作只开启上传会话（POST uploads），不上传数据。
只输出状态码、质询参数与 token 中的授权声明，不输出凭证与 token 本身。
"""

import base64
import importlib.util
import json
import re
import sys
import urllib.parse

_spec = importlib.util.spec_from_file_location("usp", __file__.rsplit("/", 1)[0] + "/upload-session-probe.py")
usp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(usp)
request, credential = usp.request, usp.credential

ACCEPT = (
    "application/vnd.oci.image.index.v1+json,application/vnd.oci.image.manifest.v1+json,"
    "application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.docker.distribution.manifest.v2+json"
)


def challenge_of(url):
    status, headers, _ = request("GET", url, {"Accept": ACCEPT})
    params = dict(re.findall(r'(\w+)="([^"]*)"', headers.get("WWW-Authenticate", "")))
    params.pop("realm", None)
    return status, params


def token_for(base, user, pwd, scopes):
    _, headers, _ = request("GET", base + "/v2/")
    params = dict(re.findall(r'(\w+)="([^"]*)"', headers.get("WWW-Authenticate", "")))
    query = [("service", params.get("service", ""))] + [("scope", s) for s in scopes]
    url = params["realm"] + ("&" if "?" in params["realm"] else "?") + urllib.parse.urlencode(query)
    basic = "Basic " + base64.b64encode(f"{user}:{pwd}".encode()).decode()
    status, _, body = request("GET", url, {"Authorization": basic})
    data = json.loads(body) if status == 200 else {}
    return status, data.get("token") or data.get("access_token") or ""


def granted(token):
    """解码 JWT 中的授权声明（不校验签名，只用于观察）"""
    try:
        payload = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        return "非 JWT，无法观察"
    return json.dumps(claims.get("access", "无 access 声明"), ensure_ascii=False)


def main():
    config, host, repo_a, tag_a, repo_b = sys.argv[1:6]
    base = "https://" + host
    user, pwd = credential(config, host)
    print(f"== {host}：A={repo_a}，B={repo_b}")

    print("-- 未认证时的质询（去掉 realm）")
    mount_query = "?mount=sha256:" + "0" * 64 + "&from=" + urllib.parse.quote(repo_a, safe="")
    for label, method, url in [
        ("GET /v2/", "GET", f"{base}/v2/"),
        ("GET A 的 manifest", "GET", f"{base}/v2/{repo_a}/manifests/{tag_a}"),
        ("POST B 开始上传", "POST", f"{base}/v2/{repo_b}/blobs/uploads/"),
        ("POST 从 A mount 到 B", "POST", f"{base}/v2/{repo_b}/blobs/uploads/{mount_query}"),
    ]:
        if method == "POST":
            status, headers, _ = request("POST", url, {"Content-Length": "0"})
            params = dict(re.findall(r'(\w+)="([^"]*)"', headers.get("WWW-Authenticate", "")))
            params.pop("realm", None)
        else:
            status, params = challenge_of(url)
        print(f"   {label}：{status}，质询参数 {params}")

    print("-- 用不同 scope 的 token 访问")
    cases = [
        ("只申请 A 的 pull", [f"repository:{repo_a}:pull"]),
        ("只申请无关仓库的 pull", ["repository:nonexistent/scope-probe:pull"]),
        ("不申请任何 scope", []),
    ]
    for label, scopes in cases:
        status, token = token_for(base, user, pwd, scopes)
        if not token:
            print(f"   {label}：换 token 失败 {status}")
            continue
        auth = {"Authorization": "Bearer " + token, "Accept": ACCEPT}
        pull_a = request("GET", f"{base}/v2/{repo_a}/manifests/{tag_a}", auth)[0]
        push_a = request("POST", f"{base}/v2/{repo_a}/blobs/uploads/", {**auth, "Content-Length": "0"})[0]
        push_b = request("POST", f"{base}/v2/{repo_b}/blobs/uploads/", {**auth, "Content-Length": "0"})[0]
        print(f"   {label}：token 授权 {granted(token)}")
        print(f"      拉 A manifest {pull_a}，在 A 开始上传 {push_a}，在 B 开始上传 {push_b}")


if __name__ == "__main__":
    main()
