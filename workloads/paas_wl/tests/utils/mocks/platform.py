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
import uuid
from typing import Dict, List, Optional

from django.conf import settings
from django.utils.crypto import get_random_string

from paas_wl.platform.applications.constants import ApplicationType
from paas_wl.platform.applications.struct_models import Application
from tests.conftest import make_structured_app_data

from .utils import mockable_function


class FakePlatformSvcClient:
    """A fake implementation for `PlatformSvcClient`"""

    @mockable_function
    def create_operation_log(
        self,
        application_id: str,
        operate_type: int,
        operator: str,
        source_object_id: Optional[str] = None,
        module_name: Optional[str] = None,
        extra_values: Optional[Dict] = None,
    ):
        pass

    @mockable_function
    def query_applications(
        self,
        uuids: Optional[List[uuid.UUID]] = None,
        codes: Optional[List[str]] = None,
        module_id: Optional[uuid.UUID] = None,
        env_id: Optional[int] = None,
        engine_app_id: Optional[uuid.UUID] = None,
    ):
        """Return a random structured data"""
        applications = []

        def _app(**kwargs) -> Application:
            """A helper function for creating Application"""
            code = get_random_string(8)
            app = Application(
                id=uuid.uuid4(),
                type=ApplicationType.DEFAULT,
                region=settings.FOR_TESTS_DEFAULT_REGION,
                code=code,
                name=code,
            )
            for k, v in kwargs.items():
                setattr(app, k, v)
            return app

        if uuids:
            for id_ in uuids:
                applications.append(_app(id=id_))
            return [make_structured_app_data(app) for app in applications]
        elif codes:
            for code in codes:
                applications.append(_app(code=code))
            return [make_structured_app_data(app) for app in applications]
        elif module_id:
            return [make_structured_app_data(app, default_module_id=str(module_id)) for app in [_app()]]
        elif env_id:
            return [make_structured_app_data(app, environment_ids=[env_id, env_id + 1]) for app in [_app()]]
        elif engine_app_id:
            return [
                make_structured_app_data(app, engine_app_ids=[str(engine_app_id), str(uuid.uuid4())])
                for app in [_app()]
            ]

        raise RuntimeError('params invalid')

    @mockable_function
    def get_market_entrance(self, code: str):
        return {'entrance': None}

    @mockable_function
    def get_addresses(self, code: str, environment: str):
        return {
            "subdomains": [
                {"host": "{environment}-{code}.example.com", "https_enabled": False},
            ],
            "subpaths": [
                {"subpath": f"/{environment}--{code}/"},
            ],
        }

    @mockable_function
    def list_addons_services(self, code: str, module_name: str, environment: str):
        return [
            {"name": "mysql", "is_provisioned": True},
            {"name": "redis", "is_provisioned": False},
            {"name": "apm", "is_provisioned": False},
        ]
