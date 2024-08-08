# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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
import pytest
from django_dynamic_fixture import G

from paasng.platform.bkapp_model.entities import DomainResolution as DomainResolutionSpec
from paasng.platform.bkapp_model.entities import HostAlias
from paasng.platform.bkapp_model.models import DomainResolution
from paasng.platform.bkapp_model.syncer import sync_domain_resolution

pytestmark = pytest.mark.django_db


class Test__sync_domain_resolution:
    def test_create(self, bk_module):
        ret = sync_domain_resolution(
            bk_module,
            DomainResolutionSpec(
                nameservers=["127.0.0.1"], host_aliases=[HostAlias(ip="1.1.1.1", hostnames=["foo.com"])]
            ),
        )

        assert ret.created_num == 1
        assert ret.updated_num == 0
        assert ret.deleted_num == 0

        obj = DomainResolution.objects.get(application=bk_module.application)
        assert obj.nameservers == ["127.0.0.1"]
        assert obj.host_aliases == [HostAlias(ip="1.1.1.1", hostnames=["foo.com"])]

    def test_update(self, bk_module):
        G(
            DomainResolution,
            application=bk_module.application,
            nameservers=["127.0.0.1"],
            host_aliases=[HostAlias(ip="1.1.1.1", hostnames=["foo.com"])],
        )

        ret = sync_domain_resolution(
            bk_module,
            DomainResolutionSpec(
                nameservers=["localhost"], host_aliases=[HostAlias(ip="192.168.1.1", hostnames=["bar.com"])]
            ),
        )

        assert ret.created_num == 0
        assert ret.updated_num == 1
        assert ret.deleted_num == 0

        obj = DomainResolution.objects.get(application=bk_module.application)
        assert set(obj.nameservers) == {"localhost", "127.0.0.1"}
        assert set(obj.host_aliases) == {
            HostAlias(ip="1.1.1.1", hostnames=["foo.com"]),
            HostAlias(ip="192.168.1.1", hostnames=["bar.com"]),
        }

    def test_delete(self, bk_module):
        G(
            DomainResolution,
            application=bk_module.application,
            nameservers=["127.0.0.1"],
            host_aliases=[HostAlias(ip="1.1.1.1", hostnames=["foo.com"])],
        )

        ret = sync_domain_resolution(
            bk_module,
            DomainResolutionSpec(nameservers=[], host_aliases=[]),
        )

        assert ret.deleted_num == 1
        assert DomainResolution.objects.filter(application=bk_module.application).exists() is False
