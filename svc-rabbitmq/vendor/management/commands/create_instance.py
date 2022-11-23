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
from paas_service.base_vendor import get_provider_cls
from vendor.command import ClusterBaseCommand
from vendor.models import InstanceBill


class Command(ClusterBaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-n", "--name", required=True, help="instance name")
        parser.add_argument("-p", "--password", required=True, help="user password")

        super().add_arguments(parser)

    def handle(self, name, password, *args, **kwargs):
        context = {
            "vhost": name,
            "user": name,
            "password": password,
        }
        bill = InstanceBill(name=name, action="create")
        cluster = self.get_cluster(*args, **kwargs)

        provider_cls = get_provider_cls()
        provider = provider_cls()
        provider.create_instance(name, bill, context, cluster)
