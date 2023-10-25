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

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.specs import ModuleSpecs

pytestmark = pytest.mark.django_db


class TestModuleSpecs:
    @pytest.mark.parametrize(
        'type_, factor_1',
        [
            (ApplicationType.DEFAULT, True),
            (ApplicationType.ENGINELESS_APP, False),
            (ApplicationType.BK_PLUGIN, False),
        ],
    )
    @pytest.mark.parametrize(
        "source_origin, factor_2",
        [
            (SourceOrigin.AUTHORIZED_VCS, True),
            (SourceOrigin.S_MART, False),
            (SourceOrigin.BK_LESS_CODE, False),
            (SourceOrigin.IMAGE_REGISTRY, False),
        ],
    )
    def test_templated_source_enabled(self, bk_app, bk_module, type_, source_origin, factor_1, factor_2):
        bk_module.source_origin = source_origin
        bk_module.save(update_fields=["source_origin"])
        bk_app.type = type_
        bk_app.save(update_fields=['type'])
        assert ModuleSpecs(bk_module).templated_source_enabled == (
            (factor_1 or (bool(bk_module.source_init_template))) and factor_2
        )

    @pytest.mark.parametrize(
        "source_origin, runtime_type, has_template_code, deploy_via_package",
        [
            (SourceOrigin.AUTHORIZED_VCS, RuntimeType.BUILDPACK, True, False),
            (SourceOrigin.S_MART, RuntimeType.BUILDPACK, False, True),
            (SourceOrigin.BK_LESS_CODE, RuntimeType.BUILDPACK, False, True),
            (SourceOrigin.IMAGE_REGISTRY, RuntimeType.CUSTOM_IMAGE, False, False),
        ],
    )
    def test_source_origin(
        self,
        bk_module,
        source_origin,
        runtime_type,
        has_template_code,
        deploy_via_package,
    ):
        bk_module.source_origin = source_origin
        bk_module.save(update_fields=["source_origin"])

        spec = ModuleSpecs(bk_module)
        assert spec.runtime_type == runtime_type
        assert spec.has_template_code == has_template_code
        assert spec.deploy_via_package == deploy_via_package
