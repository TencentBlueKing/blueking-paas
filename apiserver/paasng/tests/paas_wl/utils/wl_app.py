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

import random
from typing import Dict

from bkpaas_auth.models import User
from django.conf import settings
from django.utils.crypto import get_random_string

from paas_wl.bk_app.applications.models import Build, Release, WlApp
from paas_wl.bk_app.applications.models.config import Config
from paas_wl.bk_app.processes.kres_entities import Instance
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from tests.utils.auth import create_user


def create_wl_app(
    force_app_info: Dict | None = None,
    paas_app_code: str | None = None,
    environment: str | None = None,
    owner: User | None = None,
    cluster_name: str | None = None,
    tenant_id: str | None = DEFAULT_TENANT_ID,
) -> WlApp:
    default_environment = random.choice(["stag", "prod"])
    default_app_name = "app-" + get_random_string(length=12).lower()
    app_info = {
        "region": settings.DEFAULT_REGION_NAME,
        "name": default_app_name,
        "structure": {"web": 1, "worker": 1},
        "owner": str(owner or create_user(username="somebody")),
        "tenant_id": tenant_id,
    }

    if force_app_info:
        app_info.update(force_app_info)

    wl_app = WlApp.objects.create(**app_info)
    # Set up metadata
    Config.objects.create(
        app=wl_app,
        metadata={
            "environment": environment or default_environment,
            # Use app name as paas_app_code by default if not given
            "paas_app_code": paas_app_code or app_info["name"],
            "module_name": "default",
        },
        cluster=cluster_name or "",
    )
    return wl_app


def create_wl_instance(app: WlApp, force_instance_info: Dict | None = None) -> Instance:
    app_name = "bkapp-" + get_random_string(length=12).lower() + "-" + random.choice(["stag", "prod"])
    instance_info = {
        "app": app,
        "process_type": "web",
        "name": random.choice(["ieod", "tencent"]) + "-" + app_name + "-" + get_random_string(length=12).lower(),
        "host_ip": "x.x.x.x",
        "start_time": "",
        "state": "",
        "ready": True,
        "restart_count": 0,
        "version": 0,
    }

    if force_instance_info:
        instance_info.update(force_instance_info)

    return Instance(**instance_info)


def create_wl_release(wl_app: WlApp, build_params: Dict | None = None, release_params: Dict | None = None) -> Release:
    default_build_params = {
        "owner": create_user(username="somebody"),
        "app": wl_app,
        "slug_path": "",
        "source_type": "foo",
        "branch": "bar",
        "revision": "1",
    }

    if build_params:
        default_build_params.update(build_params)

    build_info = default_build_params
    fake_build = Build.objects.create(tenant_id=wl_app.tenant_id, **build_info)

    default_release_params = {
        "owner": create_user(username="somebody"),
        "app": wl_app,
        "version": 2,
        "summary": "",
        "failed": False,
        "build": fake_build,
        "config": wl_app.config_set.latest(),
        "procfile": {"web": "legacycommand manage.py runserver", "worker": "python manage.py celery"},
    }
    if release_params:
        default_release_params.update(release_params)
    release_info = default_release_params
    return Release.objects.create(**release_info)
