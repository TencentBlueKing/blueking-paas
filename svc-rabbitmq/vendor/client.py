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

import json
import typing
from contextlib import contextmanager
from functools import partial
from urllib.parse import urlencode, urljoin

from amqpstorm.compatibility import quote as amqp_quote
from amqpstorm.management.base import ManagementHandler
from amqpstorm.management.basic import Basic
from amqpstorm.management.channel import Channel
from amqpstorm.management.connection import Connection
from amqpstorm.management.exchange import Exchange
from amqpstorm.management.healthchecks import HealthChecks
from amqpstorm.management.http_client import HTTPClient
from amqpstorm.management.queue import Queue
from amqpstorm.management.user import User
from amqpstorm.management.virtual_host import VirtualHost
from django.conf import settings
from django.core.cache import caches
from requests import HTTPError

from .exceptions import APIError, ResourceNotFound

if typing.TYPE_CHECKING:
    from django.core.cache import BaseCache

    from .clusters import Cluster


quote = partial(amqp_quote, safe="")


class API(HTTPClient):
    Exceptions = {
        404: ResourceNotFound,
    }

    def request(self, method, path, payload=None, headers=None, params=None):
        return self._request(method, path, payload, headers, params)

    def _request(self, method, path, payload=None, headers=None, params=None):
        if isinstance(payload, (dict, list, tuple)):
            payload = json.dumps(payload)
        if params:
            path += "?%s" % urlencode(params)
        return super()._request(method, path, payload, headers)

    def _check_for_errors(self, response, json_response):
        status_code = response.status_code
        try:
            response.raise_for_status()
        except HTTPError as err:
            if not isinstance(json_response, dict) or "reason" not in json_response:
                raise APIError(str(err)) from err

            exception = self.Exceptions.get(status_code, APIError)
            raise exception(
                message=json_response.get("error", str(err)), reason=json_response["reason"], reply_code=status_code
            ) from err

    def partial(self, path: "str", method: "str", headers=None) -> "typing.Callable":
        return partial(self.request, path=path, method=method, headers=headers)


class DefinitionsHandler(ManagementHandler):
    path = "definitions/"

    def _get_path(self, virtual_host: "str"):
        if virtual_host:
            return urljoin(self.path, quote(virtual_host))
        else:
            return self.path

    def export(self, virtual_host=None):
        """Get Definitions details."""
        return self.http_client.get(self._get_path(virtual_host))

    def load(
        self,
        virtual_host=None,
        *,
        users=None,
        vhosts=None,
        permissions=None,
        topic_permissions=None,
        parameters=None,
        global_parameters=None,
        policies=None,
        queues=None,
        exchanges=None,
        bindings=None,
        rabbit_version=None,
    ):
        """Load Definitions."""
        payload = {
            "users": users,
            "vhosts": vhosts,
            "permissions": permissions,
            "topic_permissions": topic_permissions,
            "parameters": parameters,
            "global_parameters": global_parameters,
            "policies": policies,
            "queues": queues,
            "exchanges": exchanges,
            "bindings": bindings,
        }
        return self.http_client.post(
            self._get_path(virtual_host), payload={k: v for k, v in payload.items() if v is not None}
        )


class PolicyHandler(ManagementHandler):
    path: "str"

    def list(self):
        """List all policies"""
        return self.http_client.get(self.path)

    def get(self, virtual_host: "str"):
        """Get policy for specific vhost"""
        return self.http_client.get(urljoin(self.path, quote(virtual_host)))

    def delete(self, virtual_host: "str", name: "str"):
        """Delete policies for specific vhost"""
        path = "%s/%s/" % (quote(virtual_host), quote(name))
        return self.http_client.delete(urljoin(self.path, path))


class UserPolicyHandler(PolicyHandler):
    path = "policies/"

    def create(self, virtual_host: "str", name: "str", policies: "dict"):
        """Create policy for specific vhost"""
        policies["name"] = name
        policies["vhost"] = virtual_host
        path = "%s/%s/" % (quote(virtual_host), quote(name))
        return self.http_client.put(urljoin(self.path, path), payload=policies)


class LimitPolicyHandler(PolicyHandler):
    path = "vhost-limits/"

    def create(self, virtual_host: "str", name: "str", value: "int"):
        """Create policy for specific vhost"""
        path = "%s/%s/" % (quote(virtual_host), quote(name))
        return self.http_client.put(
            urljoin(self.path, path),
            payload={
                "name": name,
                "value": value,
                "vhost": virtual_host,
            },
        )


class ConnectionHandler(Connection):
    API_CONNECTION_CHANNELS = "connections/%s/channels"

    def channels(self, connection):
        """Get Channels of connection.

        :rtype: list
        """
        return self.http_client.get(self.API_CONNECTION_CHANNELS % connection)


class FederationHandler(ManagementHandler):
    def set_upstream(
        self,
        name: "str",
        uri: "str",
        virtual_host="/",
        params=None,
    ):
        value = {"uri": uri, "ack-mode": "on-confirm", "trust-user-id": False}
        if params:
            value.update(params)
        return self.http_client.put(
            f"parameters/federation-upstream/{quote(virtual_host)}/{quote(name)}",
            payload={"component": "federation-upstream", "vhost": virtual_host, "name": name, "value": value},
        )

    def delete_upstream(self, name: "str", virtual_host="/"):
        return self.http_client.delete(
            f"parameters/federation-upstream/{quote(virtual_host)}/{quote(name)}",
            payload={"component": "federation-upstream", "vhost": virtual_host, "name": name},
        )

    def list_upstream(self, virtual_host: "str"):
        return self.http_client.get(f"parameters/federation-upstream/{quote(virtual_host)}")

    def list_status(self, virtual_host: "str"):
        return self.http_client.get(f"federation-links/{quote(virtual_host)}")


class ManagementClient:
    """details https://rawcdn.githack.com/rabbitmq/rabbitmq-management/v3.7.0/priv/www/api/index.html"""

    @classmethod
    def from_cluster(cls, cluster: "Cluster"):
        return cls(api_url=cluster.management_api, username=cluster.admin, password=cluster.password)

    def __init__(self, api_url, username, password, timeout=10, verify=None, cert=None):
        self.http_client = API(api_url, username, password, timeout=timeout, verify=verify, cert=cert)
        self.basic = Basic(self.http_client)
        self.channel = Channel(self.http_client)
        self.connection = ConnectionHandler(self.http_client)
        self.exchange = Exchange(self.http_client)
        self.health_checks = HealthChecks(self.http_client)
        self.queue = Queue(self.http_client)
        self.user = User(self.http_client)
        self.virtual_host = VirtualHost(self.http_client)
        self.definitions = DefinitionsHandler(self.http_client)
        self.user_policy = UserPolicyHandler(self.http_client)
        self.limit_policy = LimitPolicyHandler(self.http_client)
        self.federation = FederationHandler(self.http_client)

        self.overview = self.http_client.partial("overview", "get")
        self.nodes = self.http_client.partial("nodes", "get")
        self.whoami = self.http_client.partial("whoami", "get")

    def alive(self, virtual_host="/") -> "bool":
        """Aliveness Test."""
        result = self.http_client.get("aliveness-test/" + quote(virtual_host))
        return result["status"] == "ok"

    def top(self):
        """Top Processes."""
        nodes = []
        for node in self.nodes():
            nodes.append(self.http_client.get(urljoin("top/", node["name"])))
        return nodes


class CacheClient(ManagementClient):
    class APIWrapper:
        undefined = object()

        def __init__(self, api, cache_name: "str", expires: "int"):
            self.api = api
            self.cache: "BaseCache" = caches[cache_name]
            self.expires = expires

        def __getattr__(self, item):
            return getattr(self.api, item)

        def _request(self, method, path, payload=None, headers=None, params=None):
            if method != "get":
                return self.api._request(method, path, payload, headers, params)

            key = f"amqp_management::{method}::{path}?{urlencode(params or {})}"

            data = self.cache.get(key, default=self.undefined)
            if data is not self.undefined:
                return data

            data = self.api._request(method, path, payload, headers, params)
            self.cache.set(key, data, self.expires)

            return data

    def __init__(
        self,
        cache_name: "str" = "default",
        expires: "int" = settings.RABBITMQ_MANAGEMENT_API_CACHE_SECONDS,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.http_client = self.APIWrapper(self.http_client, cache_name, expires)

    @contextmanager
    def disable_cache(self):
        http_client = self.http_client
        try:
            self.http_client = self.http_client.api
            yield
        finally:
            self.http_client = http_client


Client = ManagementClient
