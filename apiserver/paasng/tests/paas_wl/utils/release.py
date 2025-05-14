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

from bkpaas_auth.models import User

from paas_wl.bk_app.applications.models import Release, WlApp


def create_release(wl_app: WlApp, user: User, failed: bool = False) -> Release:
    """Create a release in given environment.

    :return: The Release object
    """
    # Don't start from 1, because "version 1" will be ignored by `any_successful()`
    # method for backward-compatibility reasons
    version = Release.objects.filter(app=wl_app).count() + 10
    # Create the Release object manually without any Build object
    return Release.objects.create(
        owner=user.username,
        app=wl_app,
        failed=failed,
        config=wl_app.latest_config,
        version=version,
        summary="",
        procfile={},
    )
