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

"""第一步，在发布请求里：首次发布时创建开发者中心应用并记下绑定。"""

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

import httpx2
from asgiref.sync import sync_to_async
from django.conf import settings

from app_spark_api.infras.bk_paas import BkPaaSApiError, BkPaaSClient, BkPaaSError, CreatedApp
from app_spark_api.publication.constants import PublicationStage
from app_spark_api.publication.models import BkPaaSAppBinding, PublicationTask
from app_spark_api.publication.steps.errors import (
    MSG_APP_NOT_RECORDED,
    AppNameTakenError,
    FailureCause,
    PublicationStepError,
    to_step_error,
)
from app_spark_api.publication.steps.progress import advance_stage

if TYPE_CHECKING:
    from app_spark_api.core.projects.models import Project

logger = logging.getLogger(__name__)


async def bind_app(
    task: PublicationTask, project: Project, client: BkPaaSClient, *, app_code: str, app_name: str
) -> None:
    """首次发布时创建开发者中心应用，然后把任务推进到打包。

    :raises PublicationStepError: 创建应用失败，消息就是给用户看的原因。
    """
    if not await BkPaaSAppBinding.objects.filter(project=project).aexists():
        try:
            app = await client.create_app(
                code=app_code, name=app_name, operator=task.operator, **build_app_tenant_kwargs(project)
            )
        except BkPaaSApiError as exc:
            # 发起前已校验过名称；这时名称再被拒，多半是有人刚刚用了它，要让用户改名而不是只看到失败。
            # 中英文名称的错误都记在不带语言后缀的 name 下。
            if exc.status_code == HTTPStatus.BAD_REQUEST and "name" in exc.fields_detail:
                raise AppNameTakenError(app_name) from exc

            raise to_step_error(exc) from exc
        except (BkPaaSError, httpx2.HTTPError) as exc:
            raise to_step_error(exc) from exc

        # 应用已经建好，记不下来时下次发布会被「应用 ID 已存在」挡住，要让用户知道找管理员处理。
        try:
            await sync_to_async(_record_app)(project, app)
        except Exception as exc:
            logger.exception("Recording developer center app %s of project %s failed", app.code, project.pk)
            raise PublicationStepError(MSG_APP_NOT_RECORDED.format(code=app.code), FailureCause.INTERNAL) from exc

    await advance_stage(task, PublicationStage.PACKAGING)


def _record_app(project: Project, app: CreatedApp) -> None:
    # 应用已经在开发者中心建好，没有绑定的话这个项目再也发布不了。
    BkPaaSAppBinding.objects.create(
        project=project, app_code=app.code, module_name=app.default_module, tenant_id=project.tenant_id
    )


def build_app_tenant_kwargs(project: Project) -> dict[str, str]:
    """Return the tenant arguments to create, or validate, the Project's application with."""
    # 非多租户时开发者中心自己固定租户信息，传了也会被忽略，所以不传。
    if not settings.ENABLE_MULTI_TENANT_MODE:
        return {}

    return {"app_tenant_mode": "single", "app_tenant_id": project.tenant_id}
