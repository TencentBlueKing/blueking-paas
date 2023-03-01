# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
"""Client for requesting platform services"""
import json
import logging
from contextlib import contextmanager
from typing import Callable, Dict, List, Optional, Union
from urllib.parse import urljoin
from uuid import UUID

import requests
from blue_krill.auth.jwt import ClientJWTAuth, JWTAuthConf
from django.conf import settings
from requests.exceptions import RequestException

from paas_wl.utils.basic import get_requests_session

from .exceptions import PlatClientRequestError, PlatResponseError

logger = logging.getLogger(__name__)


class PlatformClientConfig:
    """Config object for platform client"""

    def __init__(self, endpoint_url: str, jwt_auth_conf: JWTAuthConf):
        self.endpoint_url = endpoint_url
        self.jwt_auth_conf = jwt_auth_conf

        # all endpoints
        self.operations_url = urljoin(self.endpoint_url, '/sys/api/operations/')
        self.query_applications_url = urljoin(self.endpoint_url, '/sys/api/applications/query/')
        self.market_entrance_url = urljoin(self.endpoint_url, '/sys/api/market/applications/{code}/entrance/')
        self.finish_release_url = urljoin(self.endpoint_url, '/sys/api/applications/finish_release/')
        self.finish_archive_url = urljoin(self.endpoint_url, '/sys/api/applications/finish_archive/')
        self.retrieve_deployment = urljoin(self.endpoint_url, '/sys/api/applications/deployment/{pk}/')
        self.get_addresses_url = urljoin(
            self.endpoint_url, '/sys/api/bkapps/applications/{code}/envs/{environment}/preallocated_addresses/'
        )
        self.list_builtin_envs = urljoin(
            self.endpoint_url, '/sys/api/bkapps/applications/{code}/envs/{environment}/builtin_envs/'
        )
        # 获取增强服务启用/实例分配情况
        self.list_addons_url = urljoin(
            self.endpoint_url, 'sys/api/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/addons/'
        )

    def __str__(self) -> str:
        return f'{self.endpoint_url}'


@contextmanager
def wrap_request_exc(client: 'PlatformSvcClient'):
    try:
        logger.debug("calling platform service<%s>", client.config)
        yield
    except RequestException as e:
        raise PlatClientRequestError(f'request plat-svc error: {e}') from e
    except json.decoder.JSONDecodeError as e:
        raise PlatClientRequestError(f'invalid json response from plat-svc: {e}') from e


class PlatformSvcClient:
    """Client for platform "apiserver" service"""

    # The JWT token must use this "role" key or apiserver will decline requests
    _jwt_role = 'internal-sys'
    _default_timeout = 15

    def __init__(self, config: PlatformClientConfig):
        self.config = config
        config.jwt_auth_conf.role = self._jwt_role
        self.auth = ClientJWTAuth(config.jwt_auth_conf)
        self._session = get_requests_session()

    @staticmethod
    def validate_resp(resp: requests.Response) -> requests.Response:
        """Validate response status code"""
        if not (resp.status_code >= 200 and resp.status_code < 300):
            raise PlatResponseError(
                f'stauts code is invalid: {resp.status_code}', status_code=resp.status_code, response_text=resp.text
            )
        return resp

    def _request(self, method: Callable, **kwargs):
        kwargs.setdefault("auth", self.auth)
        kwargs.setdefault("timeout", self._default_timeout)
        return self.validate_resp(method(**kwargs))

    def create_operation_log(
        self,
        application_id: str,
        operate_type: int,
        operator: str,
        source_object_id: Optional[str] = None,
        module_name: Optional[str] = None,
        extra_values: Optional[Dict] = None,
    ):
        """Create an operation log for application

        :returns: None if creation succeeded
        :raises: PlatClientRequestError
        """
        with wrap_request_exc(self):
            self._request(
                self._session.post,
                url=self.config.operations_url,
                json={
                    'application': application_id,
                    'operate_type': operate_type,
                    'operator': operator,
                    'source_object_id': source_object_id,
                    'module_name': module_name,
                    'extra_values': extra_values,
                },
            )
            return None

    def query_applications(
        self,
        uuids: Optional[List[UUID]] = None,
        codes: Optional[List[str]] = None,
        module_id: Optional[UUID] = None,
        env_id: Optional[int] = None,
        engine_app_id: Optional[UUID] = None,
    ):
        """Query application's basic info by uuid(s), code(s), module_id, env_id,
        engine_app_id.

        :returns: list of basic application info
        :raises: PlatClientRequestError
        """
        params: Dict[str, Union[List[UUID], List[str], str, int]] = {}
        if uuids:
            params['uuid'] = [str(id) for id in uuids]
        elif codes:
            params['code'] = codes
        elif module_id:
            params['module_id'] = str(module_id)
        elif env_id:
            params['env_id'] = env_id
        elif engine_app_id:
            params['engine_app_id'] = str(engine_app_id)
        with wrap_request_exc(self):
            resp = self._request(self._session.get, url=self.config.query_applications_url, params=params)
            return resp.json()

    def get_market_entrance(self, code: str):
        """Get an application's market entrance info

        :returns: entrance dict, {'entrance': null or data}
        :raises: PlatClientRequestError
        """
        with wrap_request_exc(self):
            resp = self._request(self._session.get, url=self.config.market_entrance_url.format(code=code))
            return resp.json()

    def finish_release(self, deployment_id: str, status: str, error_detail: str):
        with wrap_request_exc(self):
            self._request(
                self._session.post,
                url=self.config.finish_release_url,
                json={"deployment_id": deployment_id, "status": status, "error_detail": error_detail},
            )

    def finish_archive(self, operation_id: str, status: str, error_detail: str):
        with wrap_request_exc(self):
            self._request(
                self._session.post,
                url=self.config.finish_archive_url,
                json={"operation_id": operation_id, "status": status, "error_detail": error_detail},
            )

    def retrieve_deployment(self, deployment_id: str):
        with wrap_request_exc(self):
            resp = self._request(self._session.get, url=self.config.retrieve_deployment.format(pk=deployment_id))
            return resp.json()

    def get_addresses(self, code: str, environment: str):
        """Get pre-allocated addresses of an environment, include both subdomains
        and subpaths.

        :param code: Application code
        :param environment: Environment name, such as "stag" or "prod"
        """
        with wrap_request_exc(self):
            resp = self._request(
                self._session.get, url=self.config.get_addresses_url.format(code=code, environment=environment)
            )
            return resp.json()

    def list_builtin_envs(self, code: str, environment: str) -> Dict[str, str]:
        """Get built-in envs of an environment

        :param code: Application code
        :param environment: Environment name, such as "stag" or "prod"
        """
        with wrap_request_exc(self):
            resp = self._request(
                self._session.get, url=self.config.list_builtin_envs.format(code=code, environment=environment)
            )
            return resp.json()["data"]

    def list_addons(self, code: str, module_name: str, environment: str):
        """获取增强服务启用/实例分配信息"""
        with wrap_request_exc(self):
            resp = self._request(
                self._session.get,
                url=self.config.list_addons_url.format(code=code, module_name=module_name, environment=environment),
            )
            return resp.json()


# A global object, always use this object when it's not None
_global_plat_client = None


def get_plat_client() -> PlatformSvcClient:
    """Create a platform client"""
    if _global_plat_client is not None:
        return _global_plat_client

    jwt_auth_conf = JWTAuthConf(**settings.INTERNAL_SERVICES_JWT_AUTH_CONF)
    _config = PlatformClientConfig(settings.PAAS_APISERVER_ENDPOINT, jwt_auth_conf)
    return PlatformSvcClient(_config)


def get_local_plat_client():
    """When "workloads" was migrated from service into module, use local client to
    call apiserver module directly.
    """
    from .local import LocalPlatformSvcClient

    return LocalPlatformSvcClient()
