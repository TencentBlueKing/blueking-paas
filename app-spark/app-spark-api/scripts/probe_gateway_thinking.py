# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Find out how bkaidev gateway models take thinking settings, and check the thinking whitelist.

The steps that use it are in the README, 「为网关模型适配 thinking」. Credentials come from the same
variables as the live tests, APP_SPARK_LIVE_BKAIDEV_ACCESS_TOKEN and APP_SPARK_LIVE_BKAIDEV_BASE_URL::

    set -a; . ~/.app-spark-live-bkaidev.env; set +a
    uv run python -m scripts.probe_gateway_thinking list
    uv run python -m scripts.probe_gateway_thinking probe hy3 hunyuan --repeat 3
    uv run python -m scripts.probe_gateway_thinking verify hy3 hunyuan

- list: the models the token can call;
- probe: sends each reasoning_effort value, and no value at all, straight to the gateway, and
  reports which values are accepted and how much the model thinks with each;
- verify: calls the models through LLMClient, i.e. through the whitelist in infras/llm/models.py,
  and reports what was actually sent and whether the model still thought.

The gateway rate-limits by app, so requests go out one at a time and back off on HTTP 429.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
from typing import Any

import attrs
import httpx2

from app_spark_api.infras.bkaidev import build_authorization_headers
from app_spark_api.infras.llm import GatewayLLMConfig, LLMCallError, LLMClient, ThinkingConfig

ACCESS_TOKEN_ENV = "APP_SPARK_LIVE_BKAIDEV_ACCESS_TOKEN"
BASE_URL_ENV = "APP_SPARK_LIVE_BKAIDEV_BASE_URL"

# 要几步推理、但答案只有一个数字：思考与否在 completion token 上差得很明显，答案本身只占几个 token。
PROMPT = "一共有 3 个苹果，吃掉 1 个，又买了 5 个，现在有几个？只回答数字。"

# None 表示请求里不带 reasoning_effort，看模型的默认行为。
EFFORTS: list[str | None] = [None, "none", "minimal", "low", "medium", "high", "xhigh", "max"]

MAX_RATE_LIMIT_RETRIES = 8


@attrs.frozen
class Sample:
    """One answer: its status, and how much the model thought for it."""

    status: int
    reasoning_chars: int = 0
    completion_tokens: int = 0
    error: str = ""


@attrs.frozen
class Gateway:
    """Where the gateway is, and the token to call it with."""

    base_url: str
    access_token: str = attrs.field(repr=False)

    @classmethod
    def from_env(cls) -> Gateway:
        access_token, base_url = os.environ.get(ACCESS_TOKEN_ENV, ""), os.environ.get(BASE_URL_ENV, "")
        if not access_token or not base_url:
            sys.exit(f"Set {ACCESS_TOKEN_ENV} and {BASE_URL_ENV} first")
        return cls(base_url=base_url.rstrip("/"), access_token=access_token)

    @property
    def headers(self) -> dict[str, str]:
        return build_authorization_headers(self.access_token)


async def send(client: httpx2.AsyncClient, method: str, url: str, **kwargs: Any) -> httpx2.Response:
    """Send one request, waiting out the gateway's rate limit."""
    for attempt in range(MAX_RATE_LIMIT_RETRIES):
        response = await client.request(method, url, **kwargs)
        if response.status_code != httpx2.codes.TOO_MANY_REQUESTS:
            return response
        await asyncio.sleep(5 * (attempt + 1))
    return response


def read_sample(response: httpx2.Response) -> Sample:
    """Read how much the model thought out of one Chat Completions answer."""
    try:
        body = response.json()
    except ValueError:
        return Sample(status=response.status_code, error=response.text[:120])
    if not response.is_success or "choices" not in body:
        # 网关把模型的报错原样带回来，里面通常写着它接受哪些取值，正是这里要看的。
        error = body.get("error")
        message = error.get("message", "") if isinstance(error, dict) else json.dumps(body, ensure_ascii=False)
        return Sample(status=response.status_code, error=message[:160])
    message = body["choices"][0]["message"]
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    return Sample(
        status=response.status_code,
        reasoning_chars=len(reasoning),
        completion_tokens=(body.get("usage") or {}).get("completion_tokens") or 0,
    )


async def list_models(gateway: Gateway) -> None:
    async with httpx2.AsyncClient(timeout=30) as client:
        response = await send(client, "GET", f"{gateway.base_url}/models", headers=gateway.headers)
    response.raise_for_status()
    for card in response.json()["data"]:
        print(card["id"], json.dumps(card.get("property"), ensure_ascii=False))


async def probe(gateway: Gateway, models: list[str], repeat: int) -> None:
    async with httpx2.AsyncClient(timeout=180) as client:
        for model in models:
            print(f"\n== {model}  （思考字数 / completion tokens，取 {repeat} 次的中位数）")
            results: dict[str | None, list[Sample]] = {}
            for effort in EFFORTS:
                body: dict[str, Any] = {"model": model, "messages": [{"role": "user", "content": PROMPT}]}
                if effort is not None:
                    body["reasoning_effort"] = effort
                samples = []
                for _ in range(repeat):
                    response = await send(
                        client, "POST", f"{gateway.base_url}/chat/completions", json=body, headers=gateway.headers
                    )
                    samples.append(read_sample(response))
                    if not response.is_success:
                        break
                results[effort] = samples
                print(f"  {effort or '(不设置)':10} {describe(samples)}")
            summarize(results)


def describe(samples: list[Sample]) -> str:
    """One line for the answers to one setting."""
    failed = [s for s in samples if s.status != httpx2.codes.OK]
    if failed:
        return f"HTTP {failed[0].status}  {failed[0].error}"
    chars = statistics.median(s.reasoning_chars for s in samples)
    tokens = statistics.median(s.completion_tokens for s in samples)
    return f"{chars:.0f} 字 / {tokens:.0f} tokens"


def _succeeded(samples: list[Sample]) -> bool:
    return all(s.status == httpx2.codes.OK for s in samples)


def summarize(results: dict[str | None, list[Sample]]) -> None:
    """Say which values the model takes, and whether none really turns its thinking off."""
    accepted = [e for e, samples in results.items() if e and _succeeded(samples)]
    rejected = [e for e in results if e and e not in accepted]
    print(f"  接受: {', '.join(accepted) or '-'}")
    print(f"  拒绝: {', '.join(rejected) or '-'}")
    default, off = results.get(None), results.get("none")
    if not default or not off or not _succeeded(default) or not _succeeded(off):
        return
    before = statistics.median(s.completion_tokens for s in default)
    after = statistics.median(s.completion_tokens for s in off)
    thought = statistics.median(s.reasoning_chars for s in off)
    # 有的模型不回传思考内容，只能看 token：答案本身只有几个 token，降到默认的四分之一以下才算关掉了。
    verdict = "能关掉思考" if thought == 0 and after <= before / 4 else "接受 none，但看起来照样思考"
    print(f"  none: {verdict}（completion tokens {before:.0f} → {after:.0f}，思考 {thought:.0f} 字）")


class Recorder(httpx2.AsyncBaseTransport):
    """Remembers the last request and answer that went through LLMClient."""

    def __init__(self) -> None:
        self._wrapped = httpx2.AsyncHTTPTransport()
        self.request_body: dict[str, Any] = {}
        self.sample: Sample | None = None

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        self.request_body = json.loads(request.content or b"{}")
        response = await self._wrapped.handle_async_request(request)
        await response.aread()
        self.sample = read_sample(response)
        return response

    async def aclose(self) -> None:
        await self._wrapped.aclose()


async def verify(gateway: Gateway, models: list[str]) -> None:
    cases = {
        "关思考（enabled=False, effort=medium）": ThinkingConfig(enabled=False, effort="medium"),
        "开思考（enabled=True, effort=high）": ThinkingConfig(enabled=True, effort="high"),
    }
    for model in models:
        print(f"\n== {model}")
        config = GatewayLLMConfig(base_url=gateway.base_url, access_token=gateway.access_token, model_id=model)
        for name, thinking in cases.items():
            recorder = Recorder()
            outcome = "成功"
            try:
                await LLMClient(config, transport=recorder).run(PROMPT, output_type=str, thinking=thinking)
            except LLMCallError as exc:
                outcome = f"失败：{exc}"
            sent = recorder.request_body.get("reasoning_effort", "(未发送)")
            sample = recorder.sample
            seen = f"{sample.reasoning_chars} 字 / {sample.completion_tokens} tokens" if sample else "-"
            print(f"  {name}: 发送 reasoning_effort={sent}，{outcome}，{seen}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list the models the token can call")
    probe_parser = commands.add_parser("probe", help="send each reasoning_effort straight to the gateway")
    probe_parser.add_argument("models", nargs="+")
    probe_parser.add_argument("--repeat", type=int, default=3, help="answers per setting (default: 3)")
    verify_parser = commands.add_parser("verify", help="call the models through LLMClient and the whitelist")
    verify_parser.add_argument("models", nargs="+")
    args = parser.parse_args()

    # 一次探测要几分钟，输出重定向到文件时也逐行写出，方便中途查看进度。
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]
    gateway = Gateway.from_env()
    match args.command:
        case "list":
            asyncio.run(list_models(gateway))
        case "probe":
            asyncio.run(probe(gateway, args.models, args.repeat))
        case "verify":
            asyncio.run(verify(gateway, args.models))


if __name__ == "__main__":
    main()
