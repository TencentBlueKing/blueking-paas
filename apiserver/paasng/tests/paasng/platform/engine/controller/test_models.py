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
import cattr

from paas_wl.infras.cluster.models import IngressConfig


def test_find_subdomain_domain():
    ing_cfg = cattr.structure(
        {
            'app_root_domains': [{"name": 'foo-1.example.com', 'https_enabled': True}],
        },
        IngressConfig,
    )
    d = ing_cfg.find_subdomain_domain('foo-1.example.com')
    assert d is not None
    assert d.https_enabled is True
    assert ing_cfg.find_subdomain_domain('foo-2.example.com') is None


def test_find_subpath_domain():
    ing_cfg = cattr.structure(
        {
            'sub_path_domains': [{"name": 'foo-1.example.com', 'https_enabled': True}],
        },
        IngressConfig,
    )
    d = ing_cfg.find_subpath_domain('foo-1.example.com')
    assert d is not None
    assert d.https_enabled is True
    assert ing_cfg.find_subpath_domain('bar.example.com') is None
