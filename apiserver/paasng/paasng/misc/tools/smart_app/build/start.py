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

import logging
from os import PathLike

from paasng.misc.tools.smart_app.constants import SourceCodeOriginType
from paasng.misc.tools.smart_app.models import SmartBuildRecord
from paasng.platform.engine.constants import JobStatus

from .tasks import execute_build, execute_build_error_callback

logger = logging.getLogger(__name__)


def create_smart_build_record(package_name: str, app_code: str, operator: str) -> SmartBuildRecord:
    """Initialize s-smart package build record

    :param package_name: The name of the source package file
    :param app_code: The code of the application
    :param operator: The username who triggers this build
    :return: The created SmartBuildRecord instance
    """
    # TODO: 添加对源码仓库的支持
    source_origin = SourceCodeOriginType.PACKAGE

    record = SmartBuildRecord.objects.create(
        source_origin=source_origin,
        package_name=package_name,
        app_code=app_code,
        status=JobStatus.PENDING,
        operator=operator,
    )
    record.refresh_from_db()
    return record


class SmartBuildTaskRunner:
    """The task runner to execute smart app build steps"""

    def __init__(self, smart_build: SmartBuildRecord, source_url: str, package_path: PathLike):
        self.smart_build = smart_build
        self.source_url = source_url
        self.package_path = package_path

    def start(self):
        smart_build_id = self.smart_build.uuid
        logger.debug("Starting new smart build task", extra={"smart_build_id": smart_build_id})
        execute_build.apply_async(
            args=(smart_build_id, self.source_url, self.package_path),
            link_error=execute_build_error_callback.s(),
        )
