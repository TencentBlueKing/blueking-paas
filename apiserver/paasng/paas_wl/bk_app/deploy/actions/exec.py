# -*- coding: utf-8 -*-
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
import logging
from typing import Dict

from attr import define, field
from six import ensure_text

from paas_wl.bk_app.deploy.actions.exceptions import BuildMissingError, CommandRerunError
from paas_wl.bk_app.deploy.app_res.utils import K8sScheduler, get_scheduler_client_by_app
from paas_wl.infras.resources.base.exceptions import PodNotSucceededError, ReadTargetStatusTimeout, ResourceDuplicate
from paas_wl.utils.constants import CommandStatus, CommandType
from paas_wl.utils.kubestatus import check_pod_health_status
from paas_wl.workloads.release_controller.hooks.kres_entities import Command as CommandKModel
from paas_wl.workloads.release_controller.hooks.models import Command
from paasng.platform.engine.utils.output import DeployStream, Style

logger = logging.getLogger(__name__)

# Max timeout seconds for waiting the command executor pod to become ready
_WAIT_FOR_READINESS_TIMEOUT = 300
_FOLLOWING_LOGS_TIMEOUT = 300


@define
class AppCommandExecutor:
    command: 'Command'
    stream: 'DeployStream'
    extra_envs: Dict = field(factory=dict)

    scheduler_client: K8sScheduler = field(init=False)
    kmodel: CommandKModel = field(init=False)
    STEP_NAME: str = field(init=False)

    def __attrs_post_init__(self):
        if not self.command.build:
            # TODO: 支持镜像部署后, 需要调整判断的条件.
            raise BuildMissingError(f"no build related to command, app_name={self.command.app.name}")

        if self.command.status != CommandStatus.PENDING.value:
            raise CommandRerunError("Can't re-run command, please create another one.")

        self.scheduler_client = get_scheduler_client_by_app(self.command.app)
        self.kmodel = CommandKModel.from_db_obj(self.command, extra_envs=self.extra_envs)
        self.STEP_NAME = CommandType(self.command.type).get_step_name()

    def perform(self):
        self.command.update_status(CommandStatus.SCHEDULED)
        try:
            self.stream.write_message(Style.Warning(f"Starting {self.STEP_NAME}"))
            self.scheduler_client.run_command(self.kmodel)

            self.scheduler_client.wait_command_logs_readiness(self.kmodel, timeout=_WAIT_FOR_READINESS_TIMEOUT)
            self.command.set_logs_was_ready()

            self.stream.write_title("executing...")
            # User interruption was allowed when first log message was received — which means the Pod
            # has entered "Running" status.

            for line in self.scheduler_client.get_command_logs(
                command=self.kmodel, timeout=_FOLLOWING_LOGS_TIMEOUT, follow=True
            ):
                line = ensure_text(line)
                self.stream.write_message(line)
            self.wait_for_succeeded()
        except ResourceDuplicate as e:
            # 上一个 Pre-Release Hook 仍未退出
            logger.exception("Duplicate pre-release-hook Pod exists")
            self.stream.write_message(
                Style.Error(f"The last {self.STEP_NAME} did not exit normally, please try again at {e.extra_value}.")
            )
            self.command.update_status(CommandStatus.FAILED)
        except ReadTargetStatusTimeout as e:
            self.command.update_status(CommandStatus.FAILED)
            pod = e.extra_value
            if pod is None:
                self.stream.write_message(
                    Style.Error("Pod is not created normally, please contact the cluster administrator.")
                )
            else:
                health_status = check_pod_health_status(pod)
                self.stream.write_message(Style.Error(health_status.message))
        except PodNotSucceededError as e:
            # Load the latest content from database, if an interruption was requested for current command
            self.command.refresh_from_db()
            if self.command.int_requested_at:
                self.stream.write_message(Style.Warning(f"{self.STEP_NAME} aborted."))
                self.command.update_status(CommandStatus.INTERRUPTED, exit_code=e.exit_code)
            else:
                logger.exception("%s execute failed", self.STEP_NAME)
                self.stream.write_message(Style.Error(e.message))
                self.command.update_status(CommandStatus.FAILED, exit_code=e.exit_code)
        except Exception:
            # 出现未捕获的异常, 直接将当前步骤置为失败
            logger.exception(f"A critical error happened during execute[{self.command}]")
            self.stream.write_message(Style.Error(f"{self.STEP_NAME} execution failed."))
            self.command.update_status(CommandStatus.FAILED)
        else:
            self.stream.write_message(Style.Warning(f"{self.STEP_NAME} execution succeed."))
            self.command.update_status(CommandStatus.SUCCESSFUL, exit_code=0)
        finally:
            self.stream.write_title(f"Cleaning up {self.STEP_NAME} container")
            self.scheduler_client.delete_command(self.kmodel)

    def wait_for_succeeded(self):
        """Wait for pod to become succeeded"""
        # The phase of a kubernetes pod was managed in a fully async way, there is not guarantee
        # it will transfer into "success/failed" immediately after "get_command_logs"
        # call finishes. So we will wait a reasonable long period such as 60 seconds.
        self.scheduler_client.wait_command_succeeded(command=self.kmodel, timeout=60)
