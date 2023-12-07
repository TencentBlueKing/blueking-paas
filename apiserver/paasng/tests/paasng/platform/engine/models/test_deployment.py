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

from paasng.platform.engine.models.deployment import Deployment

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestStreamProperties:
    def test_main_stream_obj(self, bk_deployment):
        assert bk_deployment.get_main_stream() is None
        # Create the stream object
        stream = bk_deployment.get_main_stream(create=True)
        stream.write("foobar")

        # Query the deployment again and the logs should still exist to verify data persistence
        d = Deployment.objects.get(pk=bk_deployment.pk)
        assert d.get_main_stream().lines.count() == 1

    def test_preparation_stream_obj(self, bk_deployment):
        stream = bk_deployment.get_preparation_stream(create=True)
        stream.write("foobar")

        # Make sure the two fields are not mixed
        assert bk_deployment.get_main_stream(create=True).lines.count() == 0
        assert bk_deployment.get_preparation_stream().lines.count() == 1
