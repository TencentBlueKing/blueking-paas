# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""A model configuration that could never serve the model list stops the service from starting."""

import pytest
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

BAD_AVAILABLE_LIST = {"default_model_name": "deepseek-v4-flash", "available_models": ["hy3"]}


def start_runtime_app() -> None:
    """Run the startup hook Django runs once the app registry is ready."""
    apps.get_app_config("runtime").ready()


def test_a_default_model_outside_the_available_list_stops_startup(settings):
    settings.AGENT_MODEL_SOURCE = "bkaidev"
    settings.BKAIDEV_MODEL_CONFIG = BAD_AVAILABLE_LIST

    with pytest.raises(ImproperlyConfigured, match="default_model_name 'deepseek-v4-flash' matches nothing in"):
        start_runtime_app()


def test_a_duplicated_available_model_stops_startup(settings):
    settings.AGENT_MODEL_SOURCE = "bkaidev"
    settings.BKAIDEV_MODEL_CONFIG = {"default_model_name": "hy3", "available_models": ["hy3", "hy3"]}

    with pytest.raises(ImproperlyConfigured, match="'hy3' more than once"):
        start_runtime_app()


def test_a_direct_deployment_does_not_check_the_bkaidev_configuration(settings):
    """direct 部署用不到 bkaidev 的配置，不该因为它起不来。"""
    settings.AGENT_MODEL_SOURCE = "direct"
    settings.BKAIDEV_MODEL_CONFIG = BAD_AVAILABLE_LIST

    start_runtime_app()


def test_the_default_configuration_starts(settings):
    settings.AGENT_MODEL_SOURCE = "bkaidev"
    settings.BKAIDEV_MODEL_CONFIG = {}

    start_runtime_app()
