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
import random
from typing import Dict, Optional

from bkpaas_auth.models import User
from django.conf import settings
from django.utils.crypto import get_random_string

from paas_wl.platform.applications.models.app import App
from paas_wl.platform.applications.models.build import Build
from paas_wl.platform.applications.models.config import Config
from paas_wl.platform.applications.models.release import Release
from paas_wl.workloads.processes.models import Instance

from .auth import create_user


def random_fake_app(
    force_app_info: Dict = None, paas_app_code: str = None, environment: str = None, owner: Optional[User] = None
) -> App:
    default_environment = random.choice(["stag", "prod"])
    default_app_name = 'app-' + get_random_string(length=12).lower()
    app_info = {
        "region": settings.FOR_TESTS_DEFAULT_REGION,
        "name": default_app_name,
        "structure": {"web": 1, "worker": 1},
        "owner": str(owner or create_user(username="somebody")),
    }

    if force_app_info:
        app_info.update(force_app_info)

    fake_app = App.objects.create(**app_info)
    # Set up metadata
    Config.objects.create(
        app=fake_app,
        metadata={
            "environment": environment or default_environment,
            # Use app name as paas_app_code by default if not given
            "paas_app_code": paas_app_code or app_info['name'],
            "module_name": 'default',
        },
    )
    return fake_app


def random_fake_instance(app: App, force_instance_info: Dict = None) -> Instance:
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


def release_setup(fake_app: App, build_params: Dict = None, release_params: Dict = None) -> Release:
    default_build_params = {
        "owner": create_user(username="somebody"),
        "app": fake_app,
        "slug_path": "",
        "source_type": "zzz",
        "branch": "dsdf",
        "revision": "asdf",
        "procfile": {"web": "legacycommand manage.py runserver", "worker": "python manage.py celery"},
    }

    if build_params:
        default_build_params.update(build_params)

    build_info = default_build_params
    fake_build = Build.objects.create(**build_info)

    default_release_params = {
        "owner": create_user(username="somebody"),
        "app": fake_app,
        "version": 2,
        "summary": "",
        "failed": False,
        "build": fake_build,
        "config": fake_app.config_set.latest(),
    }
    if release_params:
        default_release_params.update(release_params)

    release_info = default_release_params
    return Release.objects.create(**release_info)


def create_app(structure: Optional[Dict[str, int]] = None) -> App:
    """Create an app object for testing purpose

    :param structure: Optional app structure, default to {'web': 1}
    """
    environment = random.choice(['stag', 'prod'])
    app_name = 'app-' + get_random_string(length=12).lower()
    if structure is None:
        structure = {'web': 1}

    app = App.objects.create(
        region=settings.FOR_TESTS_DEFAULT_REGION,
        name=app_name,
        structure=structure,
        owner=create_user(username=get_random_string(length=6)),
    )
    # Set up metadata
    Config.objects.create(
        app=app,
        metadata={
            "environment": environment,
            "paas_app_code": f'paas-{app_name}',
            "module_name": 'default',
        },
    )
    return app
