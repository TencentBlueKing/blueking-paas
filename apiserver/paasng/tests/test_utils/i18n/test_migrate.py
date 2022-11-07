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
from django.apps.registry import apps
from django.db import connection
from django_dynamic_fixture import G

from paasng.engine.models.steps import DeployPhase, DeployStep
from paasng.utils.i18n.migrate import copy_field

pytestmark = pytest.mark.django_db


class TestCopyField:
    def test_normal(self):
        obj = G(DeployStep, name="test")
        assert obj.name == "test"
        assert obj.display_name_zh_cn != "test"

        with connection.schema_editor() as schema_editor:
            copy_field('engine', 'deploystep', from_field='name', to_field='display_name_zh_cn')(apps, schema_editor)

        obj.refresh_from_db()
        assert obj.display_name_zh_cn == "test"

    def test_thousands(self):
        phase = G(DeployPhase)
        objs = []
        for i in range(1, 100):
            objs.append(DeployStep(name=f"obj{i}", phase=phase))

        DeployStep.objects.bulk_create(objs)
        assert DeployStep.objects.count() == 99

        with connection.schema_editor() as schema_editor:
            copy_field('engine', 'deploystep', from_field='name', to_field='display_name_zh_cn', batch_size=2)(
                apps, schema_editor
            )

        assert set(DeployStep.objects.values_list("display_name_zh_cn", flat=True)) == {
            f"obj{i}" for i in range(1, 100)
        }
