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
"""Client for remote services
"""
import json
import logging
from contextlib import contextmanager
from dataclasses import MISSING, dataclass
from typing import Dict, List
from urllib.parse import urljoin

import requests
from blue_krill.auth.jwt import ClientJWTAuth, JWTAuthConf
from blue_krill.text import desensitize_url
from requests.exceptions import RequestException

from .exceptions import RClientResponseError, RemoteClientError

logger = logging.getLogger(__name__)


@dataclass
class RemoteSvcConfig:
    # 名称应该是唯一的
    name: str
    endpoint_url: str
    provision_params_tmpl: Dict
    jwt_auth_conf: Dict
    prefer_async_delete: bool = True
    is_ready: bool = True

    @classmethod
    def from_json(cls, data):
        fields = cls.__dataclass_fields__  # type: ignore
        for k in data.keys() ^ fields.keys():
            if k not in fields:
                raise ValueError(f"config data is not valid, {k} is an unexpected argument")

            field = fields[k]
            if field.default is MISSING and field.default_factory is MISSING:
                raise ValueError(f"config data is not valid, {k} is missing")

        try:
            return cls(**data)
        except TypeError as e:
            raise ValueError(f"config data is not valid, {e}")

    def to_json(self) -> Dict:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}  # type: ignore

    def get_jwt_auth_conf(self) -> JWTAuthConf:
        return JWTAuthConf(
            iss=self.jwt_auth_conf["iss"],
            key=self.jwt_auth_conf["key"],
            role="internal_platform",
        )

    def __post_init__(self):
        self.meta_info_url = urljoin(self.endpoint_url, "meta_info/")

        self.index_url = urljoin(self.endpoint_url, "services/")
        self.create_service_url = urljoin(self.endpoint_url, "services/")
        self.update_service_url = urljoin(self.endpoint_url, "services/{service_id}/")

        self.create_plan_url = urljoin(self.endpoint_url, "plans/")
        self.update_plan_url = urljoin(self.endpoint_url, "plans/{plan_id}/")

        self.retrieve_instance_url = urljoin(self.endpoint_url, "instances/{instance_id}/")
        self.retrieve_instance_by_name_url = urljoin(self.endpoint_url, "services/{service_id}/instances/?name={name}")
        self.update_inst_config_url = urljoin(self.endpoint_url, "instances/{instance_id}/config/")
        self.create_instance_url = urljoin(self.endpoint_url, "services/{service_id}/instances/{instance_id}/")
        self.delete_instance_url = urljoin(self.endpoint_url, "instances/{instance_id}/")
        self.async_delete_instance_url = urljoin(self.endpoint_url, "instances/{instance_id}/async_delete")
        # 增强服务绑定
        self.create_client_side_instance_url = urljoin(
            self.endpoint_url, "services/{service_id}/client-side-instances/{instance_id}/"
        )
        self.destroy_client_side_instance_url = urljoin(self.endpoint_url, "client-side-instances/{instance_id}/")

    def __str__(self):
        return f"{self.name} [{self.endpoint_url}]"


@contextmanager
def wrap_request_exc(client: "RemoteServiceClient"):
    try:
        logger.debug("[servicehub] calling remote service<%s>", client.config)
        yield
    except RequestException as e:
        logger.exception(f"unable to fetch remote services from {client.config.index_url}")
        raise RemoteClientError(f"unable to fetch remote services: {e}") from e
    except json.decoder.JSONDecodeError as e:
        logger.exception(f"invalid json response from {client.config.index_url}")
        raise RemoteClientError(f"invalid json response: {e}") from e


class RemoteServiceClient:
    """Client for remote services"""

    REQUEST_LIST_TIMEOUT = 15
    REQUEST_DELETE_TIMEOUT = 30
    REQUEST_CREATE_TIMEOUT = 300

    def __init__(self, config: RemoteSvcConfig):
        self.config = config
        self.auth = ClientJWTAuth(config.get_jwt_auth_conf())

    @staticmethod
    def validate_resp(resp: requests.Response):
        """Validate response status code"""
        if not (resp.status_code >= 200 and resp.status_code < 300):
            raise RClientResponseError(
                f"request_url: {desensitize_url(resp.url)}, status code is invalid: {resp.status_code}",
                status_code=resp.status_code,
                response_text=resp.text,
            )

    def get_meta_info(self) -> Dict:
        """Get service's meta info

        :raises: RemoteClientError
        :return: {"version": ...}
        """
        with wrap_request_exc(self):
            resp = requests.get(self.config.meta_info_url, auth=self.auth, timeout=self.REQUEST_LIST_TIMEOUT)
            self.validate_resp(resp)
            return resp.json()

    def list_services(self) -> List[Dict]:
        """List all services infos

        :raises: RemoteClientError
        :return: [<service dict>, ...]
        """
        with wrap_request_exc(self):
            resp = requests.get(self.config.index_url, auth=self.auth, timeout=self.REQUEST_LIST_TIMEOUT)
            self.validate_resp(resp)
            return resp.json()

    def create_service(self, data: Dict):
        """Create a new service

        :raises: RemoteClientError
        :return: None
        """
        with wrap_request_exc(self):
            resp = requests.put(
                self.config.create_service_url, json=data, auth=self.auth, timeout=self.REQUEST_CREATE_TIMEOUT
            )
            self.validate_resp(resp)

    def update_service(self, service_id: str, data: Dict):
        """Update the service

        :raises: RemoteClientError
        :return: None
        """
        url = self.config.update_service_url.format(service_id=service_id)
        with wrap_request_exc(self):
            resp = requests.put(url, json=data, auth=self.auth, timeout=self.REQUEST_CREATE_TIMEOUT)
            self.validate_resp(resp)

    def create_plan(self, service_id: str, data: Dict):
        """Create a new Plan for service

        :raises: RemoteClientError
        :return: None
        """
        url = self.config.create_plan_url
        data["service"] = service_id
        with wrap_request_exc(self):
            resp = requests.post(url, json=data, auth=self.auth, timeout=self.REQUEST_CREATE_TIMEOUT)
            self.validate_resp(resp)

    def update_plan(self, service_id: str, plan_id: str, data: Dict):
        """Update the Plan

        :raises: RemoteClientError
        :return: None
        """
        url = self.config.update_plan_url.format(plan_id=plan_id)
        data["service"] = service_id
        with wrap_request_exc(self):
            resp = requests.put(url, json=data, auth=self.auth, timeout=self.REQUEST_CREATE_TIMEOUT)
            self.validate_resp(resp)

    def provision_instance(self, service_id: str, plan_id: str, instance_id: str, params: Dict) -> Dict:
        """Provision a new instance

        :raises: RemoteClientError
        :return: <instance dict>
        """
        url = self.config.create_instance_url.format(service_id=service_id, instance_id=instance_id)
        payload = {"plan_id": plan_id, "params": params}
        with wrap_request_exc(self):
            resp = requests.post(url, json=payload, auth=self.auth, timeout=self.REQUEST_CREATE_TIMEOUT)
            self.validate_resp(resp)
            return resp.json()

    def retrieve_instance(self, instance_id: str) -> Dict:
        """Retrieve a provisioned instance info

        :raises: RemoteClientError
        :return: <instance dict>
        """
        url = self.config.retrieve_instance_url.format(instance_id=instance_id)
        with wrap_request_exc(self):
            resp = requests.get(url, auth=self.auth, timeout=self.REQUEST_LIST_TIMEOUT)
            self.validate_resp(resp)
            return resp.json()

    def retrieve_instance_by_name(self, service_id: str, name: str) -> Dict:
        """Retrieve a provisioned instance info by name

        :raises: RemoteClientError
        :return: <instance dict>
        """
        url = self.config.retrieve_instance_url.format(service_id=service_id, name=name)
        with wrap_request_exc(self):
            resp = requests.get(url, auth=self.auth, timeout=self.REQUEST_LIST_TIMEOUT)
            self.validate_resp(resp)
            return resp.json()

    def delete_instance(self, instance_id: str):
        """Delete a provisioned instance

        We assume the remote service is already able to recycle resources
        """
        if self.config.prefer_async_delete:
            url = self.config.async_delete_instance_url.format(instance_id=instance_id)
        else:
            url = self.config.delete_instance_url.format(instance_id=instance_id)

        with wrap_request_exc(self):
            resp = requests.delete(url, auth=self.auth, timeout=self.REQUEST_DELETE_TIMEOUT)
            self.validate_resp(resp)
            return

    def update_instance_config(self, instance_id: str, config: Dict):
        """Update an provisioned instance's config

        :raises: RemoteClientError
        """
        url = self.config.update_inst_config_url.format(instance_id=instance_id)
        with wrap_request_exc(self):
            resp = requests.put(url, json=config, auth=self.auth, timeout=self.REQUEST_CREATE_TIMEOUT)
            self.validate_resp(resp)
            return resp.json()

    def create_client_side_instance(self, service_id: str, instance_id: str, params: Dict):
        url = self.config.create_client_side_instance_url.format(service_id=service_id, instance_id=instance_id)
        with wrap_request_exc(self):
            resp = requests.post(url, json=params, auth=self.auth, timeout=self.REQUEST_CREATE_TIMEOUT)
            self.validate_resp(resp)
            return resp.json()

    def destroy_client_side_instance(self, instance_id: str):
        url = self.config.destroy_client_side_instance_url.format(instance_id=instance_id)
        with wrap_request_exc(self):
            resp = requests.delete(url, auth=self.auth, timeout=self.REQUEST_DELETE_TIMEOUT)
            self.validate_resp(resp)
            return
