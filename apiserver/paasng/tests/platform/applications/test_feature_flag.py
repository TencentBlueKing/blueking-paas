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
from unittest import mock

import pytest

from paasng.platform.applications.models import Application, get_default_feature_flags
from tests.utils.helpers import override_region_configs


class TestGetDefaultFeatureFlags:
    @pytest.mark.parametrize(
        "engine_enabled, enabled_feature_flags, default_feature_flags",
        [
            (
                True,
                [],
                {
                    'RELEASE_TO_BLUEKING_MARKET': False,
                    'RELEASE_TO_WEIXIN_QIYE': False,
                    'RELEASE_TO_WEIXIN_MINIPROGRAM': False,
                    'ACCESS_CONTROL_EXEMPT_MODE': False,
                    'PA_WEBSITE_ANALYTICS': False,
                    'PA_CUSTOM_EVENT_ANALYTICS': False,
                    'PA_INGRESS_ANALYTICS': False,
                    'PA_USER_DIMENSION_SHOW_DEPT': False,
                    'APPLICATION_DESCRIPTION': True,
                    'MODIFY_ENVIRONMENT_VARIABLE': True,
                },
            ),
            (
                False,
                [],
                {
                    'RELEASE_TO_BLUEKING_MARKET': False,
                    'RELEASE_TO_WEIXIN_QIYE': False,
                    'RELEASE_TO_WEIXIN_MINIPROGRAM': False,
                    'ACCESS_CONTROL_EXEMPT_MODE': False,
                    'PA_WEBSITE_ANALYTICS': False,
                    'PA_CUSTOM_EVENT_ANALYTICS': False,
                    'PA_INGRESS_ANALYTICS': False,
                    'PA_USER_DIMENSION_SHOW_DEPT': False,
                    'APPLICATION_DESCRIPTION': True,
                    'MODIFY_ENVIRONMENT_VARIABLE': True,
                },
            ),
            (
                True,
                ["PA_INGRESS_ANALYTICS"],
                {
                    'RELEASE_TO_BLUEKING_MARKET': False,
                    'RELEASE_TO_WEIXIN_QIYE': False,
                    'RELEASE_TO_WEIXIN_MINIPROGRAM': False,
                    'ACCESS_CONTROL_EXEMPT_MODE': False,
                    'PA_WEBSITE_ANALYTICS': False,
                    'PA_CUSTOM_EVENT_ANALYTICS': False,
                    'PA_INGRESS_ANALYTICS': True,
                    'PA_USER_DIMENSION_SHOW_DEPT': False,
                    'APPLICATION_DESCRIPTION': True,
                    'MODIFY_ENVIRONMENT_VARIABLE': True,
                },
            ),
            (
                False,
                ["PA_INGRESS_ANALYTICS"],
                {
                    'RELEASE_TO_BLUEKING_MARKET': False,
                    'RELEASE_TO_WEIXIN_QIYE': False,
                    'RELEASE_TO_WEIXIN_MINIPROGRAM': False,
                    'ACCESS_CONTROL_EXEMPT_MODE': False,
                    'PA_WEBSITE_ANALYTICS': False,
                    'PA_CUSTOM_EVENT_ANALYTICS': False,
                    'PA_INGRESS_ANALYTICS': False,
                    'PA_USER_DIMENSION_SHOW_DEPT': False,
                    'APPLICATION_DESCRIPTION': True,
                    'MODIFY_ENVIRONMENT_VARIABLE': True,
                },
            ),
            (
                False,
                [
                    'RELEASE_TO_BLUEKING_MARKET',
                    'RELEASE_TO_WEIXIN_QIYE',
                    'RELEASE_TO_WEIXIN_MINIPROGRAM',
                    'ACCESS_CONTROL_EXEMPT_MODE',
                    'PA_WEBSITE_ANALYTICS',
                    'PA_CUSTOM_EVENT_ANALYTICS',
                    'PA_INGRESS_ANALYTICS',
                    'PA_USER_DIMENSION_SHOW_DEPT',
                ],
                {
                    'RELEASE_TO_BLUEKING_MARKET': True,
                    'RELEASE_TO_WEIXIN_QIYE': True,
                    'RELEASE_TO_WEIXIN_MINIPROGRAM': True,
                    'ACCESS_CONTROL_EXEMPT_MODE': True,
                    'PA_WEBSITE_ANALYTICS': True,
                    'PA_CUSTOM_EVENT_ANALYTICS': True,
                    'PA_INGRESS_ANALYTICS': False,
                    'PA_USER_DIMENSION_SHOW_DEPT': True,
                    'APPLICATION_DESCRIPTION': True,
                    'MODIFY_ENVIRONMENT_VARIABLE': True,
                },
            ),
        ],
    )
    def test_override(self, db, bk_app, engine_enabled, enabled_feature_flags, default_feature_flags):
        def update_region_hook(config):
            # Make user access control switch enable by default
            config['enabled_feature_flags'] = enabled_feature_flags

        with override_region_configs(bk_app.region, update_region_hook), mock.patch.object(
            Application, "engine_enabled", mock.PropertyMock(return_value=engine_enabled)
        ):
            assert get_default_feature_flags(bk_app) == default_feature_flags
