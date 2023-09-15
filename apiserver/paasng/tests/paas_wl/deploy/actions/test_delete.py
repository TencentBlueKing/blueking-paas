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

from paas_wl.deploy.actions.delete import delete_module_related_res
from paas_wl.networking.ingress.models import Domain
from paas_wl.platform.applications.models import Build, Release, WlApp

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestDeleteModuleRelatedRes:
    def test_normal(self, bk_user, bk_module, bk_stag_env, bk_stag_wl_app):
        # Setup data
        Domain.objects.create(name='example.com', module_id=bk_module.id, environment_id=bk_stag_env.id)
        build = Build.objects.create(owner=bk_user.username, app=bk_stag_wl_app)
        bk_stag_wl_app.release_set.new(bk_user.username, build=build, procfile={'web': 'true'})

        assert Domain.objects.filter(module_id=bk_module.id).exists()
        assert WlApp.objects.filter(uuid=bk_stag_env.engine_app_id).exists()
        assert Release.objects.filter(app__uuid=bk_stag_env.engine_app_id).exists()

        delete_module_related_res(bk_module)

        assert not Domain.objects.filter(module_id=bk_module.id).exists()
        assert not WlApp.objects.filter(uuid=bk_stag_env.engine_app_id).exists()
        assert not Release.objects.filter(app__uuid=bk_stag_env.engine_app_id).exists()
