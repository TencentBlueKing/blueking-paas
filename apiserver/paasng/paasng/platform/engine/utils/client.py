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
"""Engine services module
"""
from typing import Dict

from django.utils.functional import cached_property

from paas_wl.bk_app.applications.constants import ArtifactType
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.applications.models.build import Build
from paas_wl.workloads.images.models import AppImageCredential


class EngineDeployClient:
    """A high level client for engine, provides functions related with deployments"""

    def __init__(self, engine_app):
        self.engine_app = engine_app

    @cached_property
    def wl_app(self) -> WlApp:
        """Make 'wl_app' a property so tests using current class won't panic when
        initializing because not data can be found in workloads module.
        """
        return self.engine_app.to_wl_obj()

    def create_build(
        self,
        image: str,
        extra_envs: Dict[str, str],
        artifact_type: ArtifactType = ArtifactType.NONE,
    ) -> str:
        """Create the **fake** build for Image Type App"""
        build = Build.objects.create(
            app=self.wl_app,
            env_variables=extra_envs,
            image=image,
            artifact_type=artifact_type,
        )
        return str(build.uuid)

    def upsert_image_credentials(self, registry: str, username: str, password: str):
        """Update an engine app's image credentials, which will be used to pull image."""
        AppImageCredential.objects.update_or_create(
            app=self.wl_app,
            registry=registry,
            defaults={"username": username, "password": password},
        )
