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

"""
A Command to deploy a Blueking Application.
"""

import json
import logging
from functools import wraps
from typing import cast

from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.models import user_id_encoder
from blue_krill.redis_tools.messaging import StreamChannelSubscriber
from blue_krill.web.std_error import APIError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from paasng.core.core.storages.redisdb import get_default_redis
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.constants import ImagePullPolicy
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.deploy.start import DeployTaskRunner, initialize_deployment
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.utils.output import Style
from paasng.platform.engine.utils.query import DeploymentGetter
from paasng.platform.engine.workflow import DeploymentCoordinator, ServerSendEvent
from paasng.platform.sourcectl.constants import VersionType
from paasng.platform.sourcectl.models import VersionInfo
from paasng.platform.sourcectl.version_services import get_version_service
from paasng.utils.error_codes import error_codes

REVISION_HELP_TEXT = """\
revision 描述需要部署的版本.
对于 git/svn 应用, 支持部署 branch or tag, 对于 s-mart 应用, 支持 package or image.

Example:
git/svn tag: 'tag:你的标签'
git/svn branch: 'branch:你的分支名'
s-mart(二进制): 'package:源码包版本号'
s-mart(镜像): 'image:镜像 tag'
"""
logger = logging.getLogger("commands")


class DeployError(CommandError):
    def __init__(self, msg: str, return_code: int = 1):
        super().__init__(msg, returncode=return_code)
        self.msg = msg


def handle_error(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except APIError as e:
            self.stderr.write(f"{type(e)}: {e.message}")
        except DeployError:
            raise
        except Exception as e:
            logger.exception("command error.")
            raise CommandError("- 部署失败, 未捕获的异常情况❌") from e

    return wrapper


def get_subscriber(channel_id):
    subscriber = StreamChannelSubscriber(channel_id, redis_db=get_default_redis())
    channel_state = subscriber.get_channel_state()
    if channel_state == "none":
        raise error_codes.CHANNEL_NOT_FOUND
    return subscriber


class Command(BaseCommand):
    """手动触发部署指令, 并轮询部署结果"""

    def add_arguments(self, parser):
        parser.add_argument("--app-code", dest="app_code", required=True, help="应用code")
        parser.add_argument("--module", dest="module_name", required=True, help="模块名称")
        parser.add_argument("--env", dest="environment", required=True, help="部署环境", choices=["stag", "prod"])
        parser.add_argument(
            "-u", "--operator", dest="operator", required=False, type=str, default="admin", help="当前操作人"
        )
        parser.add_argument("--revision", dest="smart_revision", required=True, type=str, help=REVISION_HELP_TEXT)
        parser.add_argument(
            "--image-pull-policy",
            dest="image_pull_policy",
            required=False,
            choices=ImagePullPolicy.get_values(),
            default=ImagePullPolicy.IF_NOT_PRESENT,
            help="镜像拉取策略",
        )
        parser.add_argument(
            "--force", dest="force", default=False, action="store_true", help="强制部署, 无论上次部署是否还在进行."
        )
        parser.add_argument(
            "--redeploy",
            dest="redeploy",
            action="store_true",
            help="启用此选项后，会重新部署。默认情况下，如果相同的版本已经成功部署过，则跳过部署。",
        )

    @handle_error
    def handle(
        self,
        operator,
        app_code,
        module_name,
        environment,
        smart_revision,
        image_pull_policy,
        force,
        redeploy,
        *args,
        **options,
    ):
        operator = get_user_by_user_id(user_id_encoder.encode(settings.USER_TYPE, operator))

        application = Application.objects.get(code=app_code)
        module = application.get_module(module_name=module_name)
        env = module.get_envs(environment)
        version_service = get_version_service(module, operator=operator.pk)

        version_type, version_name = smart_revision.split(":", 1)

        # 针对 s-mart 镜像应用, 后端部署接口调整为仅支持 version_type 值为 tag, 因此这里将 image 转换为 tag
        if version_type == VersionType.IMAGE.value and application.is_smart_app:
            version_type = VersionType.TAG.value

        revision = version_service.extract_smart_revision(smart_revision)
        version_info = VersionInfo(revision, version_name, version_type)
        advanced_options = None
        if image_pull_policy:
            advanced_options = {"image_pull_policy": image_pull_policy}

        if not redeploy:
            latest_deployment = DeploymentGetter(env).get_latest_succeeded()
            if latest_deployment and latest_deployment.get_version_info() == version_info:
                self.stdout.write(
                    f"应用({app_code})模块({module_name})的当前版本({revision})已成功部署过，跳过本次部署!"
                )
                return

        coordinator = DeploymentCoordinator(env)
        if not coordinator.acquire_lock():
            raise DeployError("部署失败，已有部署任务进行中，请刷新查看❌")

        with coordinator.release_on_error():
            deployment = initialize_deployment(
                env=env,
                operator=operator,
                version_info=version_info,
                advanced_options=advanced_options,
            )
            DeployTaskRunner(deployment).start()

            self.stdout.write("---------------------------------")
            self.stdout.write("- 正在部署⌛")
            self.stdout.write("---------------------------------")

            self.waiting(deployment=deployment)

            deployment.refresh_from_db()
            if deployment.release_status != JobStatus.SUCCESSFUL:
                raise DeployError(f"部署失败, {deployment.err_detail}❌")
            else:
                self.stdout.write("---------------------------------")
                self.stdout.write("- 部署成功✅")
                self.stdout.write("---------------------------------")

    def waiting(self, deployment: Deployment):
        """Waiting deploy task, and watching logs"""
        subscriber = get_subscriber(deployment.id)
        for data in subscriber.get_events():
            e = ServerSendEvent.from_raw(data)

            if e.is_internal:
                continue

            if e.event == "title":
                self.stdout.write(e.data, Style.Yellow)
            elif e.event == "message":
                if isinstance(e.data, str):
                    message = cast(str, e.data)
                    self.stdout.write(json.loads(message)["line"])
                else:
                    self.stdout.write(e.data)
