# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""发布对 Project 生命周期信号的响应。"""

from typing import TYPE_CHECKING, Any

from django.dispatch import receiver

from app_spark_api.core.projects.exceptions import ProjectDeletionError
from app_spark_api.core.projects.signals import project_deleting
from app_spark_api.publication import steps
from app_spark_api.publication.services import afail_pending_tasks

if TYPE_CHECKING:
    from app_spark_api.core.projects.models import Project


@receiver(project_deleting)
async def end_publication_tasks(sender: Any, project: Project, **kwargs: Any) -> None:
    """End the Project's running publication before its resources go away."""
    # 准备任务只在任务仍在进行中时才发部署，结束之后就不会再把已删项目部署上去。
    # 已经提交的部署在开发者中心照常进行，要到开发者中心下架。
    try:
        await afail_pending_tasks(project, steps.MSG_PROJECT_DELETED)
    except Exception as exc:
        raise ProjectDeletionError("publication task") from exc
