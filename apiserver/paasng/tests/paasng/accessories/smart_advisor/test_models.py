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
import logging

import pytest

from paasng.accessories.smart_advisor import AppPLTag, AppSDKTag, force_tag
from paasng.accessories.smart_advisor.models import cleanup_module, get_tags, tag_module
from paasng.accessories.smart_advisor.tags import DeploymentFailureTag, get_dynamic_tag

logger = logging.getLogger(__name__)


pytestmark = pytest.mark.django_db


class TestModuleTagger:
    def test_normal(self, bk_module):
        tag_module(bk_module, [force_tag("app-pl:python"), force_tag("app-sdk:celery")])
        assert get_tags(bk_module) == {AppPLTag("python"), AppSDKTag("celery")}

    def test_cleanup(self, bk_module):
        tag_module(bk_module, [force_tag("app-pl:python"), force_tag("app-sdk:celery")])
        cleanup_module(bk_module)
        assert get_tags(bk_module) == set()


class TestGetDynamicTag:
    @pytest.mark.parametrize(
        "tag_str,tag_obj",
        [
            ("deploy-failure:fix_procfile", DeploymentFailureTag("fix_procfile")),
            ("app-pl:python", AppPLTag("python")),
            # When expected tag is None, a ValueError will be raised
            ("invalid-type:value", None),
            ("invalid_tag_string", None),
        ],
    )
    def test_normal(self, tag_str, tag_obj):
        if not tag_obj:
            with pytest.raises(ValueError):
                get_dynamic_tag(tag_str)
        else:
            assert get_dynamic_tag(tag_str) == tag_obj
