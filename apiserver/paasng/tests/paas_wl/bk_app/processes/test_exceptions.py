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

from unittest.mock import Mock

import pytest
from kubernetes.dynamic.exceptions import NotFoundError

from paas_wl.bk_app.processes.exceptions import ScaleProcessError


class TestScaleProcessError:
    @pytest.mark.parametrize(
        ("exc", "expected"),
        [
            (ScaleProcessError(proc_type="web"), "scale web failed"),
            (ScaleProcessError(proc_type="web", exception=KeyError("foo")), "scale web failed, reason: 'foo'"),
            (ScaleProcessError(message="unknown error"), "unknown error"),
        ],
    )
    def test_string_representation(self, exc, expected):
        assert str(exc) == expected

    def test_caused_by_not_found(self):
        assert ScaleProcessError(proc_type="web", exception=KeyError("foo")).caused_by_not_found() is False

        # Build a NotFoundError
        _exc = Mock(
            body=(
                b'{"kind":"Status","apiVersion":"v1","metadata":{},"status":"Failure",'
                b'"message":"namespaces \\"foo\\" not found","reason":"NotFound",'
                b'"details":{"name":"bkapp-backend-app-prod","kind":"namespaces"},"code":404}\n'
            ),
        )
        exc = NotFoundError(_exc)
        assert ScaleProcessError(proc_type="web", exception=exc).caused_by_not_found() is True
