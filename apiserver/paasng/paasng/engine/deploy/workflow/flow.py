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
"""Core components for deploy workflow"""
import logging
import time
from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING, Optional

import redis
from django.utils.encoding import force_text
from django.utils.translation import gettext as _

from paasng.engine.constants import JobStatus
from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.engine.deploy.exceptions import DeployShouldAbortError
from paasng.engine.deploy.infra.output import DeployStream, StreamType, Style, get_default_stream
from paasng.engine.exceptions import StepNotInPresetListError
from paasng.engine.models import Deployment, DeployPhaseTypes
from paasng.engine.models.operations import ModuleEnvironmentOperations
from paasng.engine.signals import post_appenv_deploy, post_phase_end
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.core.storages.redisdb import get_default_redis
from paasng.utils.error_message import find_coded_error_message

if TYPE_CHECKING:
    from paasng.engine.models.phases import DeployPhase
    from paasng.engine.models.steps import DeployStep as DeployStepModel


logger = logging.getLogger(__name__)


class DeployProcedure:
    """A application deploy procedure wrapper

    :param stream: stream for writing title and messages
    :param title: title of current step
    """

    TITLE_PREFIX: str = '正在'

    def __init__(
        self,
        stream: DeployStream,
        deployment: Optional[Deployment],
        title: str,
        phase: 'DeployPhase',
    ):
        self.stream = stream
        self.title = title
        self.deployment = deployment
        self.phase = phase

        self.step_obj = self._get_step_obj(title)

    def __enter__(self):
        self.stream.write_title(f'{self.TITLE_PREFIX}{self.title}')

        if self.step_obj:
            self.step_obj.mark_and_write_to_steam(self.stream, JobStatus.PENDING)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            if self.step_obj:
                self.step_obj.mark_and_write_to_steam(self.stream, JobStatus.SUCCESSFUL)

            return False

        # Only exception `DeployShouldAbortError` should be outputed directly into the stream,
        # While other exceptions should be masked as "Unknown error" instead for better user
        # experience.
        if exc_type in [DeployShouldAbortError]:
            msg = _('步骤 [{title}] 出错了，原因：{reason}。').format(
                title=Style.Title(self.title), reason=Style.Warning(exc_val)
            )
        else:
            msg = _("步骤 [{title}] 出错了，请稍候重试。").format(title=Style.Title(self.title))

        coded_message = find_coded_error_message(exc_val)
        if coded_message:
            msg += coded_message

        logger.exception(msg)
        self.stream.write_message(msg, StreamType.STDERR)

        if self.step_obj:
            self.step_obj.mark_and_write_to_steam(self.stream, JobStatus.FAILED)
        if self.phase:
            self.phase.mark_and_write_to_steam(self.stream, JobStatus.FAILED)
        return False

    def _get_step_obj(self, title: str) -> Optional['DeployStepModel']:
        if not self.deployment:
            return None
        logger.debug("trying to get step by title<%s>", title)
        try:
            return self.phase.get_step_by_name(title)
        except StepNotInPresetListError as e:
            logger.info("%s, skip", e.message)
            return None


class DeploymentStateMgr:
    """Deployment state manager"""

    def __init__(self, deployment: Deployment, phase_type: 'DeployPhaseTypes', stream: Optional[DeployStream] = None):
        self.deployment = deployment
        self.stream = stream or get_default_stream(deployment)
        self.phase_type = phase_type

    @classmethod
    def from_deployment_id(cls, deployment_id: str, phase_type: 'DeployPhaseTypes'):
        deployment = Deployment.objects.get(pk=deployment_id)
        return cls(deployment=deployment, phase_type=phase_type)

    def update(self, **fields):
        return self.deployment.update_fields(**fields)

    def finish(self, status: JobStatus, err_detail: str = '', write_to_stream: bool = True):
        """finish a deployment

        :param status: the final status of deployment
        :param err_detail: only useful when status is "FAILED"
        :param write_to_stream: write the raw error detail message to stream, default to True
        """
        if status not in JobStatus.get_finished_states():
            raise ValueError(f'{status} is not a valid finished status')
        if write_to_stream and err_detail:
            self.stream.write_message(self._stylize_error(err_detail, status), stream=StreamType.STDERR)

        post_phase_end.send(self, status=status, phase=self.phase_type)
        self.stream.close()
        self.update(status=status.value, err_detail=err_detail)

        # Record operation
        ModuleEnvironmentOperations.objects.filter(object_uid=self.deployment.id).update(status=status.value)

        if status == JobStatus.SUCCESSFUL and self.deployment.app_environment.is_offlined:
            # 任意部署任务成功，下架状态都需要被更新
            self.deployment.app_environment.is_offlined = False
            self.deployment.app_environment.save(update_fields=['is_offlined'])

        # Release deploy lock
        DeploymentCoordinator(self.deployment.app_environment).release_lock(expected_deployment=self.deployment)

        # Trigger signal
        post_appenv_deploy.send(self.deployment.app_environment, deployment=self.deployment)

    @staticmethod
    def _stylize_error(error_detail: str, status: JobStatus) -> str:
        """Add color and format for error_detail"""
        if status == JobStatus.INTERRUPTED:
            return Style.Warning(error_detail)
        elif status == JobStatus.FAILED:
            return Style.Error(error_detail)
        else:
            return error_detail


class DeploymentCoordinator:
    """Manage environment's deploy status to avoid duplicated deployments

    :param type: lock type, default to "deploy"
    :param timeout: operation timeout, the default value is 15 minutes.
    :param redis_db: optional redis database object
    """

    # The lock will be released anyway after {DEFAULT_LOCK_TIMEOUT} seconds
    DEFAULT_LOCK_TIMEOUT = 15 * 60
    # A placeholder value for lock
    DEFAULT_TOKEN = 'None'
    # If not any poll in 90s, assume the poller is failed
    POLLING_TIMEOUT = 90

    def __init__(
        self,
        env: ModuleEnvironment,
        type: str = 'deploy',
        timeout: Optional[float] = None,
        redis_db: Optional[redis.Redis] = None,
    ):
        self.env = env
        self.redis = redis_db or get_default_redis()

        self.key_name_lock = f'env:{env.pk}:{type}:lock'
        self.key_name_deployment = f'env:{env.pk}:{type}:deployment'
        self.key_name_latest_polling_time = f'env:{env.pk}:{type}:latest_polling_time'
        # use milliseconds
        self.timeout_ms = int((timeout or self.DEFAULT_LOCK_TIMEOUT) * 1000)

    def acquire_lock(self) -> bool:
        """Acquire lock to start a new deployment"""
        if self.redis.set(self.key_name_lock, self.DEFAULT_TOKEN, nx=True, px=self.timeout_ms):
            return True
        return False

    def release_lock(self, expected_deployment: Optional[Deployment] = None):
        """Finish a deployment process, release the deploy lock

        :param expected_deployment: if given, will raise ValueError when the ongoing deployment is
            not identical with given deployment
        :raises: ValueError when deployment not matched
        """

        def execute_release(pipe):
            if expected_deployment:
                deployment_id = pipe.get(self.key_name_deployment)
                if deployment_id and (force_text(deployment_id) != str(expected_deployment.pk)):
                    raise ValueError('Can not release a lock that is not owned by given deployment')

            pipe.delete(self.key_name_lock)
            # Clean deployment key
            pipe.delete(self.key_name_deployment)
            # Clean latest polling time key
            pipe.delete(self.key_name_latest_polling_time)

        self.redis.transaction(execute_release, self.key_name_deployment)

    def set_deployment(self, deployment: Deployment):
        """Set current deployment"""
        self.redis.set(self.key_name_deployment, str(deployment.pk), px=self.timeout_ms)
        self.update_polling_time()

    def get_current_deployment(self) -> Optional[Deployment]:
        """Get current deployment"""
        deployment_id = self.redis.get(self.key_name_deployment)
        if deployment_id:
            # 若存在部署进程，但数据上报已经超时，则认为部署失败，主动解锁并失效
            if self.status_polling_timeout:
                self.release_lock()
                return None

            return Deployment.objects.get(pk=force_text(deployment_id))
        return None

    def update_polling_time(self):
        """存储状态报告时间，将在 query 时候调用"""
        self.redis.set(self.key_name_latest_polling_time, time.time(), px=self.timeout_ms)

    @property
    def status_polling_timeout(self) -> bool:
        """检查报告时间是否超时"""
        latest_polling_time = self.redis.get(self.key_name_latest_polling_time)
        # 如果没有上次报告状态时间，则认为未超时，并设置查询时间为上次报告时间
        if not latest_polling_time:
            self.update_polling_time()
            return False

        return (time.time() - float(force_text(latest_polling_time))) > self.POLLING_TIMEOUT

    @contextmanager
    def release_on_error(self):
        try:
            yield
        except Exception:
            self.release_lock()
            raise


class DeployStep:
    """Base class for a deploy step"""

    PHASE_TYPE: Optional[DeployPhaseTypes] = None

    def __init__(self, deployment: Deployment, stream: Optional[DeployStream] = None):
        if not self.PHASE_TYPE:
            raise NotImplementedError("phase type should be specific firstly")

        self.deployment = deployment

        self.engine_app = deployment.get_engine_app()
        self.module_environment = deployment.app_environment
        self.engine_client = EngineDeployClient(self.engine_app)
        self.version_info = deployment.version_info

        self.stream = stream or get_default_stream(deployment)
        self.state_mgr = DeploymentStateMgr(deployment=self.deployment, stream=self.stream, phase_type=self.PHASE_TYPE)

        self.phase = self.deployment.deployphase_set.get(type=self.PHASE_TYPE)
        self.procedure = partial(DeployProcedure, self.stream, self.deployment, phase=self.phase)
        self.procedure_force_phase = partial(DeployProcedure, self.stream, self.deployment)

    @classmethod
    def from_deployment_id(cls, deployment_id: str):
        deployment = Deployment.objects.get(pk=deployment_id)
        return cls(deployment=deployment)

    @staticmethod
    def procedures(func):
        """A decorator which update deployment automatically when exception happens"""

        def decorated(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                deployment = self.deployment
                logger.exception(f"A critical error happened during deploy[{deployment.pk}], {e}")
                # The error message has already been written to stream by DeployProcedure context
                # So we will not write the error message again.
                self.state_mgr.finish(JobStatus.FAILED, str(e), write_to_stream=False)

        return decorated
