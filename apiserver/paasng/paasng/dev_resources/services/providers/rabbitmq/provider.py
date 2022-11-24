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
"""
rabbitmq provider
"""
from typing import Dict

import requests

from paasng.dev_resources.services.utils import gen_unique_id, generate_password

from ..base import BaseProvider, InstanceData
from .exceptions import CreateRabbitMQFail


class RabbitMQProvider(BaseProvider):
    display_name = "RabbitMQ 通用申请服务"
    """
    RabbitMQ资源处理
    """

    def __init__(self, config):
        self._host = config['host']
        self._port = config['port']
        self._user = config['user']
        self._password = config['password']

        # the port which user will connect on
        self.port = config['http_port']
        self.url_prefix = "http://%s:%s" % (self._host, self._port)
        self.auth = (self._user, self._password)
        self.headers = {'content-type': 'application/json'}

    def test_connection(self):
        url = '%s/api/overview' % self.url_prefix
        r = requests.get(url, auth=self.auth)
        if r.status_code == 200:
            return
        if r.status_code == 401:
            raise CreateRabbitMQFail(u"管理员账户信息有误")
        else:
            raise CreateRabbitMQFail(u"rabbitmq服务异常")

    def put_request(self, path, json=None):
        url = '%s%s' % (self.url_prefix, path)
        r = requests.put(url=url, headers=self.headers, auth=self.auth, json=json)
        return r.status_code in [201, 204]

    def del_request(self, path, json=None):
        url = '%s%s' % (self.url_prefix, path)
        return requests.delete(url=url, headers=self.headers, auth=self.auth, json=json).status_code in [201, 204]

    def get_request(self, path, json=None):
        url = '%s%s' % (self.url_prefix, path)
        return requests.get(url=url, headers=self.headers, auth=self.auth, json=json).json()

    def create(self, params) -> InstanceData:
        """
        create rabbitmq user and vhost
        """
        preferred_name = params.get('engine_app_name')
        # get_unique_id
        uid = gen_unique_id(preferred_name)
        rabbitmq_vhost = uid
        rabbitmq_user = uid

        # 可重入, 保证密码不变
        rabbitmq_password = generate_password()

        self.test_connection()

        # 1. 创建vhost
        path = '/api/vhosts/%s' % rabbitmq_vhost
        is_success = self.put_request(path)
        if not is_success:
            raise CreateRabbitMQFail(u"创建vhost失败")

        # 2. 创建账户
        path = '/api/users/%s' % rabbitmq_user
        json = {"password": rabbitmq_password, "tags": "management"}
        is_success = self.put_request(path, json)
        if not is_success:
            raise CreateRabbitMQFail(u"创建账户失败")

        # 3. vhost 授权
        path = '/api/permissions/%s/%s' % (rabbitmq_vhost, rabbitmq_user)
        json = {"configure": ".*", "write": ".*", "read": ".*"}
        is_success = self.put_request(path, json)
        if not is_success:
            raise CreateRabbitMQFail(u"vhost授权失败")

        credentials = {
            "host": self._host,
            "port": self.port,
            "vhost": rabbitmq_vhost,
            "user": rabbitmq_user,
            "password": rabbitmq_password,
        }

        return InstanceData(credentials=credentials, config={})

    def delete(self, instance_data: InstanceData):
        """
        return True, message
        """
        option = instance_data.credentials
        rabbitmq_vhost = option['RABBITMQ_VHOST']
        rabbitmq_user = option['RABBITMQ_USER']

        self.test_connection()

        # 1. 删除vhost
        path = '/api/vhosts/%s' % rabbitmq_vhost
        is_success = self.del_request(path)
        if not is_success:
            return False, u"删除vhost失败"

        # 2. 删除账户
        path = '/api/users/%s' % rabbitmq_user
        json: Dict = {}
        is_success = self.del_request(path, json)
        if not is_success:
            return False, u"删除账户失败"

        return

    def patch(self, params):
        """
        return True, message
        """
        pass

    def stats(self, resource):
        raise NotImplementedError
