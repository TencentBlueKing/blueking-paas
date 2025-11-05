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

from unittest import mock

import pytest

from paasng.misc.tools.smart_app.output import ConsoleStream, RedisWithModelStream

pytestmark = pytest.mark.django_db


class TestConsoleStream:
    def test_write_output(self):
        lines: list[str] = []
        with mock.patch("sys.stdout") as stdout:
            stdout.write.side_effect = lines.append
            stream = ConsoleStream()
            stream.write_title("test_title")
            stream.write_message("test_message")

        assert "".join(lines) == "[TITLE]: test_title\ntest_message\n"


class TestRedisWithModelStream:
    def test_write_and_persist(self, smart_build):
        stream = RedisWithModelStream(smart_build.stream, mock.MagicMock())
        stream.write_message("test message")
        stream.write_title("test title")

        assert smart_build.stream.lines.count() == 2
        lines = list(smart_build.stream.lines.values_list("line", flat=True))
        assert "test message\n" in lines
        assert "[TITLE]: test title\n" in lines
