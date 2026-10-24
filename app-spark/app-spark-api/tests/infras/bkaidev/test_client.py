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

"""Reading the bkaidev gateway's model list, and refusing one it never promised."""

import json

import httpx2
import pytest

from app_spark_api.infras.bkaidev import BkAidevGatewayClient, BkAidevGatewayError, GatewayModel, GatewayModelProperty

BASE_URL = "https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1"
ACCESS_TOKEN = "user-access-token"

# 与网关实际返回的卡片同形，含本服务不读的 permission、support_window 等字段，以及顶层的 trace_id。
HY3_CARD = {
    "id": "hy3",
    "object": "model",
    "created": 1792662210,
    "owned_by": "aidev",
    "root": "hy3",
    "parent": None,
    "permission": [{"id": "modelperm-1", "object": "model_permission", "allow_sampling": True}],
    "property": {
        "default": True,
        "support_vision": False,
        "support_tools": True,
        "support_window": True,
        "support_summary": True,
        "max_model_len": 256000,
        "is_self_host": True,
    },
}


def make_client(handler) -> BkAidevGatewayClient:
    return BkAidevGatewayClient(base_url=BASE_URL, access_token=ACCESS_TOKEN, transport=httpx2.MockTransport(handler))


def make_answer(status: int = 200, **kwargs):
    def answer(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status, **kwargs)

    return answer


async def test_the_models_are_read_off_a_real_shaped_answer():
    client = make_client(make_answer(json={"object": "list", "data": [HY3_CARD], "trace_id": "abc"}))

    assert await client.list_models() == [
        GatewayModel(
            code="hy3",
            properties=GatewayModelProperty(support_tools=True, support_vision=False, max_model_len=256000),
        )
    ]


async def test_the_users_token_is_the_only_credential_sent():
    requests: list[httpx2.Request] = []

    def answer(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json={"object": "list", "data": []})

    await make_client(answer).list_models()

    (request,) = requests
    assert str(request.url) == f"{BASE_URL}/models"
    assert json.loads(request.headers["X-Bkapi-Authorization"]) == {"access_token": ACCESS_TOKEN}
    assert "Authorization" not in request.headers


async def test_a_card_that_says_nothing_about_tools_is_not_read_as_unable():
    """没给能力位和明确说不支持是两回事，后者才会被剔出列表。"""
    cards = [{"id": "bare"}, {"id": "partial", "property": {"max_model_len": 32000}}]
    client = make_client(make_answer(json={"object": "list", "data": cards}))

    bare, partial = await client.list_models()

    assert bare.properties is None
    assert partial.properties == GatewayModelProperty(support_tools=None, support_vision=False, max_model_len=32000)


async def test_a_failed_answer_names_the_status_and_not_the_body():
    client = make_client(make_answer(500, text=f"upstream exploded near {ACCESS_TOKEN}"))

    with pytest.raises(BkAidevGatewayError) as exc_info:
        await client.list_models()

    assert "500" in str(exc_info.value)
    assert ACCESS_TOKEN not in str(exc_info.value)


async def test_an_unreachable_gateway_is_a_gateway_error():
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection refused", request=request)

    with pytest.raises(BkAidevGatewayError, match="ConnectError"):
        await make_client(refuse).list_models()


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        pytest.param(make_answer(text="<html>gateway</html>"), "not JSON", id="not-json"),
        pytest.param(make_answer(json={"object": "list"}), "data", id="no-data"),
        pytest.param(
            make_answer(json={"object": "list", "data": [{"object": "model"}]}), "data[0]", id="a-card-without-id"
        ),
        # 被宽松转换成 True 的话，一个不能调工具的模型就混进了列表。
        pytest.param(
            make_answer(json={"object": "list", "data": [{"id": "m", "property": {"support_tools": "false"}}]}),
            "support_tools",
            id="a-flag-that-is-not-a-bool",
        ),
        pytest.param(
            make_answer(json={"object": "list", "data": [{"id": "m", "property": {"max_model_len": True}}]}),
            "max_model_len",
            id="a-length-that-is-a-bool",
        ),
    ],
)
async def test_an_answer_that_is_not_a_model_list_is_refused_by_name(answer, reason):
    with pytest.raises(BkAidevGatewayError) as exc_info:
        await make_client(answer).list_models()

    assert reason in str(exc_info.value)
