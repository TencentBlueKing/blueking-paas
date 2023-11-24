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

import pytest

from paas_wl.workloads.networking.ingress.models import AppDomainSharedCert

pytestmark = pytest.mark.django_db(databases=["workloads"])


class TestAppDomainSharedCert:
    @pytest.mark.parametrize(
        "cns,hostname,expected",
        [
            ("*.foo.com;bar.com", "bar.com", True),
            ("*.foo.com;bar.com", "baz.foo.com", True),
            ("*.foo.com;bar.com", "foo.com", False),
            ("*.foo.com;bar.com", "foobar.com", False),
        ],
    )
    def test_match_hostname(self, cns, hostname, expected):
        cert_obj = AppDomainSharedCert.objects.create(auto_match_cns=cns)
        assert cert_obj.match_hostname(hostname) is expected
