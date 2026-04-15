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

from dataclasses import dataclass, field
from typing import List, Optional
from unittest import mock

import pytest

from paas_wl.bk_app.agent_sandbox.image_cache import ImageCacheStatus
from paasng.platform.agent_sandbox.image_build.image_cache import pre_pull_sandbox_image
from paasng.platform.agent_sandbox.models import ImageBuildRecord

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@dataclass
class StubImageCache:
    """Stub ImageCache for testing without real K8s cluster."""

    name: str
    client: mock.MagicMock
    images: List[str] = field(default_factory=list)
    image_pull_secrets: List[str] = field(default_factory=list)
    status: Optional[ImageCacheStatus] = None

    _upsert_called: bool = False
    _delete_called: bool = False

    def upsert(self):
        """Mark upsert was called."""
        self._upsert_called = True

    def delete(self):
        """Mark delete was called."""
        self._delete_called = True

    def get(self) -> Optional["StubImageCache"]:
        """Return self with succeeded status for _wait_for_image_cache."""
        self.status = ImageCacheStatus(status="Succeeded")
        return self


def test_pre_pull_sandbox_image(build: ImageBuildRecord):
    """Test successful image pre-pull flow."""
    stub_image_cache = StubImageCache(
        name=f"pre-pull-{build.uuid.hex}",
        client=mock.MagicMock(),
    )

    with (
        mock.patch("paasng.platform.agent_sandbox.image_build.image_cache.ensure_image_credential"),
        mock.patch(
            "paasng.platform.agent_sandbox.image_build.image_cache.ImageCache",
            return_value=stub_image_cache,
        ),
        mock.patch("time.sleep"),
    ):
        pre_pull_sandbox_image(str(build.uuid))

    assert stub_image_cache._upsert_called is True
    assert stub_image_cache._delete_called is True
    assert stub_image_cache.status is not None
    assert stub_image_cache.status.status == "Succeeded"
