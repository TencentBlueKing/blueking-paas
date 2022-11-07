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
from django.urls import reverse
from django_dynamic_fixture import G

from paasng.platform.modules import serializers as slzs
from paasng.platform.modules.helpers import ModuleRuntimeBinder, ModuleRuntimeManager
from paasng.platform.modules.models import AppBuildPack

pytestmark = pytest.mark.django_db


class TestModuleRuntimeViewSetV2:
    def test_list(self, api_client, bk_app, bk_module, buildpack, slugbuilder, slugrunner):
        url = reverse(
            "api.modules.runtime.available_list",
            kwargs={
                "code": bk_app.code,
                "module_name": bk_module.name,
            },
        )
        response = api_client.get(url)

        results = response.data["results"]
        result = results[0]
        assert len(results) == 1
        assert result["image"] == slugbuilder.name
        assert result["image"] == slugrunner.name
        assert len(result["buildpacks"]) == 1

        assert result["buildpacks"][0]["name"] == buildpack.name

    def test_retrieve_empty(self, api_client, bk_app, bk_module):
        url = reverse(
            "api.modules.runtime",
            kwargs={
                "code": bk_app.code,
                "module_name": bk_module.name,
            },
        )
        response = api_client.get(url)
        result = response.data
        assert result["image"] is None
        assert result["slugbuilder"] is None
        assert result["slugrunner"] is None
        assert len(result["buildpacks"]) == 0

    def test_retrieve(self, api_client, bk_app, bk_module, image_name, buildpack, slugbuilder, slugrunner):
        url = reverse(
            "api.modules.runtime",
            kwargs={
                "code": bk_app.code,
                "module_name": bk_module.name,
            },
        )
        binder = ModuleRuntimeBinder(bk_module, slugbuilder)
        binder.bind_image(slugrunner, slugbuilder)
        binder.bind_buildpack(buildpack)

        response = api_client.get(url)
        result = response.data
        assert result["image"] == image_name
        assert result["slugbuilder"] == slzs.AppSlugBuilderMinimalSLZ(slugbuilder).data
        assert result["slugrunner"] == slzs.AppSlugRunnerMinimalSLZ(slugrunner).data
        assert len(result["buildpacks"]) == 1
        assert result["buildpacks"][0] == slzs.AppBuildPackMinimalSLZ(buildpack).data

    def test_bind(self, api_client, bk_app, bk_module, image_name, buildpack, slugbuilder, slugrunner):
        url = reverse(
            "api.modules.runtime",
            kwargs={
                "code": bk_app.code,
                "module_name": bk_module.name,
            },
        )

        response = api_client.post(
            url,
            data={
                "image": slugbuilder.name,
                "buildpacks_id": [buildpack.id],
            },
        )
        result = response.data

        assert result["image"] == image_name
        assert result["slugbuilder_id"] == slugbuilder.id
        assert result["slugrunner_id"] == slugrunner.id
        assert len(result["buildpacks_id"]) == 1
        assert result["buildpacks_id"][0] == buildpack.id

    def test_rebind(self, api_client, bk_app, bk_module, image_name, buildpack, slugbuilder, slugrunner):
        url = reverse(
            "api.modules.runtime",
            kwargs={
                "code": bk_app.code,
                "module_name": bk_module.name,
            },
        )

        api_client.post(
            url,
            data={
                "image": slugbuilder.name,
                "buildpacks_id": [buildpack.id],
            },
        )
        new_bp = G(AppBuildPack, name="x", region=bk_module.region, language=bk_module.language)
        slugbuilder.buildpacks.add(new_bp)

        response = api_client.post(
            url,
            data={
                "image": slugbuilder.name,
                "buildpacks_id": [new_bp.id],
            },
        )
        result = response.data
        assert result["image"] == image_name
        assert result["slugbuilder_id"] == slugbuilder.id
        assert result["slugrunner_id"] == slugrunner.id
        assert len(result["buildpacks_id"]) == 1
        assert result["buildpacks_id"][0] == new_bp.id

    def test_bind_multi_buildpacks(
        self, api_client, bk_app, bk_module, image_name, buildpack, slugbuilder, slugrunner
    ):
        url = reverse(
            "api.modules.runtime",
            kwargs={
                "code": bk_app.code,
                "module_name": bk_module.name,
            },
        )

        api_client.post(
            url,
            data={
                "image": slugbuilder.name,
                "buildpacks_id": [buildpack.id],
            },
        )
        new_bp = G(AppBuildPack, name="x", region=bk_module.region, language=bk_module.language)
        slugbuilder.buildpacks.add(new_bp)

        manager = ModuleRuntimeManager(bk_module)

        response = api_client.post(
            url,
            data={
                "image": slugbuilder.name,
                "buildpacks_id": [new_bp.id, buildpack.id],
            },
        )
        result = response.data

        assert len(result["buildpacks_id"]) == 2
        assert result["buildpacks_id"] == [new_bp.id, buildpack.id]
        assert result["buildpacks_id"] == [bp.id for bp in manager.list_buildpacks()]

        response = api_client.post(
            url,
            data={
                "image": slugbuilder.name,
                "buildpacks_id": [
                    buildpack.id,
                    new_bp.id,
                ],
            },
        )
        result = response.data
        assert len(result["buildpacks_id"]) == 2
        assert result["buildpacks_id"] == [buildpack.id, new_bp.id]
        assert result["buildpacks_id"] == [bp.id for bp in manager.list_buildpacks()]
