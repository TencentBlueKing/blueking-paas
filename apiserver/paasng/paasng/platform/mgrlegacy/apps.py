# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

from paasng.utils.addons import AddonsUrlRegister, PlugableAppConfig
from paasng.utils.basic import re_path


class MgrlegacyConfig(PlugableAppConfig):
    name = "paasng.platform.mgrlegacy"
    default = True


def contribute_to_app(app_name):
    from paasng.urls import urlpatterns as base_urlpatterns

    from .urls import urlpatterns as extra_urlpatterns

    AddonsUrlRegister(base_urlpatterns).register(re_path("", (extra_urlpatterns, None, None)))
