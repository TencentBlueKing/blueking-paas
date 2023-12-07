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

from paasng.platform.engine.logs import DeploymentLogStreams, get_all_logs, make_channel_stream

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def test_make_channel_stream(bk_deployment):
    assert make_channel_stream(bk_deployment, "main") is not None
    assert make_channel_stream(bk_deployment, "preparation") is not None

    # Make streams that does not exists yet will raise an error
    with pytest.raises(ValueError, match=r".*does not exist"):
        make_channel_stream(bk_deployment, "build_proc")
    with pytest.raises(ValueError, match=r".*does not exist"):
        make_channel_stream(bk_deployment, "pre_release_cmd")


class TestDeploymentLogs:
    def test_main_stream_obj(self, bk_deployment):
        log_streams = DeploymentLogStreams(bk_deployment)
        assert log_streams.main_stream is None

        # Create the stream object
        stream = log_streams.main_stream_for_write
        stream.write("foobar")
        stream_for_read = log_streams.main_stream
        assert stream_for_read is not None
        assert stream_for_read.lines.count() == 1, "The log lines should have been written successfully."

    def test_preparation_stream_obj(self, bk_deployment):
        log_streams = DeploymentLogStreams(bk_deployment)
        log_streams.preparation_stream_for_write.write("foobar")

        # Make sure the two fields are not mixed
        assert log_streams.main_stream_for_write.lines.count() == 0
        assert log_streams.preparation_stream_for_write.lines.count() == 1


def test_get_all_logs(bk_deployment):
    logs = get_all_logs(bk_deployment)
    assert logs.strip() == ""
