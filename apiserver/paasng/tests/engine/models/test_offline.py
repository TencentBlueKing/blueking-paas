# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import pytest

from paasng.engine.models.offline import OfflineOperation

pytestmark = pytest.mark.django_db


class TestOfflineOperation:
    def test_set_failed(self, bk_prod_env):
        offline_op = OfflineOperation.objects.create(app_environment=bk_prod_env)
        offline_op.set_failed('failed message')
        assert offline_op.status == 'failed'

    def test_set_successful(self, bk_prod_env):
        offline_op = OfflineOperation.objects.create(app_environment=bk_prod_env)
        offline_op.set_successful()
        assert offline_op.status == 'successful'
