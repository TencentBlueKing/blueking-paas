# -*- coding: utf-8 -*-
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


import logging
from typing import Any, Self
from urllib.parse import quote

import requests

from paas_wl.infras.cluster.models import ClusterE2BConfig

from .clusters import get_e2b_cluster_config
from .constants import (
    GATEWAY_CREATE_TIMEOUT_SECONDS,
    GATEWAY_REQUEST_TIMEOUT_SECONDS,
)
from .exceptions import (
    E2BGatewayError,
    E2BGatewayNotFound,
    E2BGatewayTimeout,
    E2BGatewayUnavailable,
)

logger = logging.getLogger(__name__)


class E2BGatewayClient:
    """某个集群的 e2b 控制面网关客户端。

    持有的是该集群的真实网关凭证，绝不下发给用户；用户侧用的是平台自签发的 key。

    :param config: 目标集群的 e2b 配置，提供网关地址与凭证
    """

    def __init__(self, config: ClusterE2BConfig):
        self.config = config
        self.base_url = config.control_plane_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers["X-API-Key"] = config.api_key

    @classmethod
    def for_cluster(cls, cluster_name: str) -> Self:
        """按集群名取 e2b 配置并构造客户端。

        编排层绝大多数路径都是「已知集群名 → 取配置 → 打网关」，走这一处即可。
        """
        return cls(get_e2b_cluster_config(cluster_name))

    def create_sandbox(self, payload: dict[str, Any]) -> dict[str, Any]:
        """认领或拉起一个沙箱。

        超时窗口比其余接口宽：池子未命中时网关要现场拉起实例。

        :param payload: 透传给网关的创建请求体，至少含 templateID
        """
        resp = self._request("POST", "/sandboxes", json=payload, timeout=GATEWAY_CREATE_TIMEOUT_SECONDS)
        return resp.json()

    def get_sandbox(self, sandbox_id: str) -> dict[str, Any]:
        """查询沙箱详情。

        每次调用网关都会重新签发 envdAccessToken，这是令牌过期后的续期路径，
        """
        resp = self._request("GET", f"/sandboxes/{quote(sandbox_id, safe='')}")
        return resp.json()

    def list_sandboxes(self) -> list[dict[str, Any]]:
        """列出该网关凭证名下的全部沙箱。

        注意这里返回的是平台在这个集群下创建的所有沙箱，**不能直接下发给用户**
        """
        resp = self._request("GET", "/v2/sandboxes")
        data = resp.json()
        if not isinstance(data, list):
            raise E2BGatewayError(f"expected a list from gateway, got {type(data).__name__}")
        return data

    def kill_sandbox(self, sandbox_id: str) -> None:
        """销毁沙箱。"""
        self._request("DELETE", f"/sandboxes/{quote(sandbox_id, safe='')}")

    def set_timeout(self, sandbox_id: str, timeout: int) -> None:
        """重设沙箱的存活时长，对应 SDK 的 ``set_timeout``。"""
        self._request("POST", f"/sandboxes/{quote(sandbox_id, safe='')}/timeout", json={"timeout": timeout})

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        timeout: int = GATEWAY_REQUEST_TIMEOUT_SECONDS,
        **kwargs: Any,
    ) -> requests.Response:
        """发起请求并把传输层与 HTTP 层的失败收敛成本模块的异常。

        错误信息里只保留方法、路径与状态码。网关的响应体可能带有平台凭证或其他
        租户的沙箱标识，不进异常消息，避免经错误响应外泄。
        """
        try:
            resp = self._session.request(method, f"{self.base_url}{path}", timeout=timeout, **kwargs)
            resp.raise_for_status()
        except requests.Timeout as exc:
            raise E2BGatewayTimeout(f"gateway timed out on {method} {path}") from exc
        except requests.HTTPError as exc:
            status = exc.response.status_code
            if status == 404:
                raise E2BGatewayNotFound(f"gateway returned 404 on {method} {path}") from exc
            logger.warning("e2b gateway returned %s on %s %s: %s", status, method, path, exc.response.text[:500])
            raise E2BGatewayError(f"gateway returned {status} on {method} {path}") from exc
        except requests.RequestException as exc:
            # 连接被拒、DNS 失败、TLS 握手失败等，都归为「暂时连不上」
            raise E2BGatewayUnavailable(f"cannot reach gateway on {method} {path}: {exc}") from exc
        else:
            return resp
