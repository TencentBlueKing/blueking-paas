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

from paasng.platform.engine.configurations.provider import EnvVariablesProviders

pytestmark = pytest.mark.django_db


def test_providers(bk_stag_env, bk_deployment):
    providers = EnvVariablesProviders()

    @providers.register_env
    def test_get_vars(env):
        return {'FOO': 'bar', 'FOOBAR': 'z'}

    @providers.register_env
    def test_get_vars_2(env):
        return {'FOO': '1', 'BAR': str(env.id)}

    @providers.register_deploy
    def test_get_vars_deploy(deployment):
        return {'DEP': str(deployment.id)}

    assert providers.gather(bk_stag_env) == {'FOO': '1', 'BAR': str(bk_stag_env.id), 'FOOBAR': 'z'}
    assert providers.gather(bk_stag_env, bk_deployment) == {
        'FOO': '1',
        'BAR': str(bk_stag_env.id),
        'FOOBAR': 'z',
        'DEP': str(bk_deployment.id),
    }
