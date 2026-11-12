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

"""开发者中心为 AppSpark 开放的应用态系统 API 的类型化 HTTP 客户端。

只用应用态凭证（app_code + app_secret）鉴权，不带用户身份：发布在后台推进，用户关掉页面、登录态过期后
仍要继续。operator 放在请求体里，只用于记录操作人。AppSpark 只发布默认模块的生产环境，开发者中心对
AppSpark 角色也只放行 prod。接口文档见 apiserver 的 support-files/apigw/api_doc/。
"""

import json
from typing import Any, Self

import httpx2
from django.conf import settings

from app_spark_api.infras.bk_paas.entities import CreatedApp, Deployment, DeploymentResult, structure_payload
from app_spark_api.infras.bk_paas.exceptions import (
    BkPaaSApiError,
    BkPaaSConfigurationError,
    BkPaaSUnavailableError,
)

# 蓝鲸网关公共鉴权头，值是 JSON 字符串。
BKAPI_AUTHORIZATION_HEADER = "X-Bkapi-Authorization"
# 单次请求的超时秒数。最慢的是上传源码包：开发者中心要先把包下载下来，它对 20MB 以内的包承诺 30 秒内返回。
DEFAULT_TIMEOUT_SECONDS = 60.0


class BkPaaSClient:
    """Call the developer center's system APIs as this service, over the API gateway.

    Example::

        async with BkPaaSClient.from_settings() as client:
            app = await client.create_app(code="demo-a1b2", name="Demo", operator="alice")

    :param base_url: 网关上开发者中心的根地址（含环境），如 https://bkapi.example.com/api/bkpaas3/prod。
    :param app_code: 本服务的应用 ID。
    :param app_secret: 本服务的应用密钥，只进请求头。
    :param timeout: 单次请求超时秒数。
    :param transport: 测试注入的 httpx2 transport。
    """

    def __init__(
        self,
        base_url: str,
        app_code: str,
        app_secret: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx2.AsyncClient(
            base_url=self.base_url,
            headers={BKAPI_AUTHORIZATION_HEADER: json.dumps({"bk_app_code": app_code, "bk_app_secret": app_secret})},
            timeout=timeout,
            transport=transport,
        )

    @classmethod
    def from_settings(cls, *, transport: httpx2.AsyncBaseTransport | None = None) -> BkPaaSClient:
        """Build a client from this service's gateway template and app identity.

        :raises BkPaaSConfigurationError: 网关模板、环境或网关名缺失。
        """
        return cls(
            base_url=build_gateway_base_url(),
            app_code=settings.APP_CODE,
            app_secret=settings.APP_SECRET,
            transport=transport,
        )

    async def aclose(self) -> None:
        """Close the underlying connection pool."""
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def create_app(
        self,
        code: str,
        name: str,
        operator: str,
        app_tenant_mode: str | None = None,
        app_tenant_id: str | None = None,
    ) -> CreatedApp:
        """Create a standard cloud-native application whose default module is sourced from AppSpark.

        :param operator: 应用管理员用户名，必须是开发者中心里的真实用户。
        :param app_tenant_mode: 多租户模式下的应用租户模式；非多租户时开发者中心忽略它。
        :param app_tenant_id: 多租户模式下的租户 ID。
        """
        payload: dict[str, Any] = {"code": code, "name": name, "operator": operator}
        if app_tenant_mode is not None:
            payload["app_tenant_mode"] = app_tenant_mode
            payload["app_tenant_id"] = app_tenant_id or ""

        response = await self._client.post("/system/bkapps/app_spark/", json=payload)
        return CreatedApp.from_payload(read_gateway_json(response))

    async def upload_package_via_link(  # noqa: PLR0917
        self,
        code: str,
        module: str,
        package_url: str,
        version: str,
        operator: str,
        build_method: str,
    ) -> None:
        """Have the developer center download a source package from a link and store it as a version.

        :param version: 源码包版本号，之后部署时用同一个值。
        :param build_method: buildpack 或 dockerfile，会同时改掉模块的构建方式。
        """
        # 任务重启后会重做上传这一步，同一版本号再传一次必须成功，所以允许覆盖。
        payload = {
            "package_url": package_url,
            "version": version,
            "operator": operator,
            "build_method": build_method,
            "allow_overwrite": True,
        }
        response = await self._client.post(
            f"{self._build_module_path(code, module)}/source_package/link/", json=payload
        )
        read_gateway_json(response)

    async def deploy(self, code: str, module: str, version: str, operator: str) -> Deployment:
        """Deploy an uploaded source package version to the production environment."""
        payload = {"version_type": "package", "version_name": version, "revision": version, "operator": operator}
        response = await self._client.post(
            f"{self._build_module_path(code, module)}/envs/prod/deployments/", json=payload
        )
        return structure_payload(read_gateway_json(response), Deployment)

    async def get_deployment_result(self, code: str, module: str, deployment_id: str) -> DeploymentResult:
        """Return where a deployment has got to."""
        response = await self._client.get(
            f"{self._build_module_path(code, module)}/deployments/{deployment_id}/result/"
        )
        return structure_payload(read_gateway_json(response), DeploymentResult)

    @staticmethod
    def _build_module_path(code: str, module: str) -> str:
        return f"/system/bkapps/applications/{code}/modules/{module}"


def read_gateway_json(response: httpx2.Response) -> Any:
    """Return a 2xx response's JSON body, or raise the error a non-2xx one describes."""

    if response.is_success:
        try:
            return response.json()
        except ValueError as exc:
            raise BkPaaSUnavailableError(
                f"The developer center answered HTTP {response.status_code} with a body that is not JSON"
            ) from exc

    raise _build_api_error(response)


def _build_api_error(response: httpx2.Response) -> BkPaaSApiError:
    """Read the error a non-2xx response describes.

    开发者中心自己的错误体是 {code, detail, fields_detail}；网关层拒绝时是 {code, message}，code 为数字。
    两种都读不出来时退回 HTTP 状态说明。
    """
    try:
        body = response.json()
    except ValueError:
        body = None

    if not isinstance(body, dict):
        return BkPaaSApiError(response.status_code, response.reason_phrase or f"HTTP {response.status_code}")

    raw_code = body.get("code")
    message = body.get("detail") or body.get("message") or response.reason_phrase or f"HTTP {response.status_code}"
    fields_detail = body.get("fields_detail")
    return BkPaaSApiError(
        response.status_code,
        _flatten_message(message),
        code=None if raw_code is None else str(raw_code),
        fields_detail=fields_detail if isinstance(fields_detail, dict) else None,
    )


def _flatten_message(message: Any) -> str:
    # 参数校验错误的 detail 偶尔是列表或字典，统一转成一行文字，方便直接展示。
    if isinstance(message, str):
        return message

    return json.dumps(message, ensure_ascii=False)


def build_gateway_base_url() -> str:
    """Return the developer center's root on the API gateway, stage included.

    :raises BkPaaSConfigurationError: 网关模板不含 {api_name}，或缺少环境、网关名。
    """
    tmpl = _require_setting("BK_API_URL_TMPL", settings.BK_API_URL_TMPL)
    stage = _require_setting("BKPAAS_APIGW_ENVIRONMENT", settings.BKPAAS_APIGW_ENVIRONMENT)
    api_name = _require_setting("BKPAAS_APIGW_NAME", settings.BKPAAS_APIGW_NAME)

    # format 遇到没用上的关键字参数不会报错，模板里没有 {api_name} 时会拼出少了网关名的地址，所以先显式检查。
    if "{api_name}" not in tmpl:
        raise BkPaaSConfigurationError(f"BK_API_URL_TMPL must contain {{api_name}}: {tmpl!r}")

    # 除 {api_name} 之外的占位符或残缺的花括号，format 会抛这几种异常。
    try:
        root = tmpl.format(api_name=api_name).rstrip("/")
    except (KeyError, IndexError, ValueError) as exc:
        raise BkPaaSConfigurationError(
            f"BK_API_URL_TMPL may contain no placeholder other than {{api_name}}: {tmpl!r}"
        ) from exc

    return f"{root}/{stage}"


def _require_setting(name: str, value: object) -> str:
    """Return a non-empty settings string, or say which key the operator must set."""
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise BkPaaSConfigurationError(f"{name} is required to call the developer center")

    return text
