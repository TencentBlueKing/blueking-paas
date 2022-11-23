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

---

Infrastructure functions and tools for deploy
"""
import abc
import json
import logging
import re
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, ClassVar, Dict, List, Optional, Union

import redis
from blue_krill.redis_tools.messaging import StreamChannel
from django.conf import settings
from django.utils.encoding import force_text
from django.utils.translation import gettext as _

from paasng.dev_resources.servicehub.manager import mixed_service_mgr
from paasng.dev_resources.servicehub.sharing import ServiceSharingManager
from paasng.engine.constants import DeployEventStatus, JobStatus
from paasng.engine.controller.exceptions import BadResponse
from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.engine.deploy.env_vars import env_vars_providers
from paasng.engine.deploy.exceptions import DeployShouldAbortError
from paasng.engine.exceptions import DuplicateNameInSamePhaseError, InternalEventFormatError, StepNotInPresetListError
from paasng.engine.models import Deployment, DeployPhaseTypes
from paasng.engine.models.config_var import generate_blobstore_env_vars, generate_builtin_env_vars, get_config_vars
from paasng.engine.models.operations import ModuleEnvironmentOperations
from paasng.engine.signals import post_appenv_deploy, post_phase_end
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.core.storages.redisdb import get_default_redis
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.region.models import get_region
from paasng.publish.entrance.domains import Domain, ModuleEnvDomains
from paasng.publish.entrance.exposer import get_bk_doc_url_prefix
from paasng.publish.entrance.subpaths import ModuleEnvSubpaths, Subpath
from paasng.utils import termcolors
from paasng.utils.error_message import find_coded_error_message

if TYPE_CHECKING:
    from paasng.engine.models.phases import DeployPhase
    from paasng.engine.models.steps import DeployStep as DeployStepModel


logger = logging.getLogger(__name__)


def make_style(*args, **kwargs):
    colorful = termcolors.make_style(*args, **kwargs)

    def dynamic_style(text):
        if settings.COLORFUL_TERMINAL_OUTPUT:
            return colorful(text)
        return termcolors.no_color(text)

    return dynamic_style


class Style:
    """
    Valid colors:
        ANSI Color: 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
        XTerm Color: [0-256]
        Hex Color: #000000 ~ #FFFFFF
    see also: https://en.wikipedia.org/wiki/X11_color_names#Clashes_between_web_and_X11_colors_in_the_CSS_color_scheme

    Valid options:
        'bold', 'underscore', 'blink', 'reverse', 'conceal', 'noreset'
    """

    Title = make_style(fg='#c4c6cc', opts=('bold',))
    Error = make_style(fg='#e82f2f', opts=('bold',))
    Warning = make_style(fg='#ff9c01', opts=('bold',))
    Comment = make_style(fg='#3a84ff', opts=('bold',))
    NoColor = termcolors.no_color

    Black = make_style(fg='black', opts=('bold',))
    Red = make_style(fg='red', opts=('bold',))
    Green = make_style(fg='green', opts=('bold',))
    Yellow = make_style(fg='yellow', opts=('bold',))
    Blue = make_style(fg='blue', opts=('bold',))
    Magenta = make_style(fg='magenta', opts=('bold',))
    Cyan = make_style(fg='cyan', opts=('bold',))
    White = make_style(fg='white', opts=('bold',))


class StreamType(str, Enum):
    STDOUT = 'STDOUT'
    STDERR = 'STDERR'


class DeployStream(metaclass=abc.ABCMeta):
    """Abstraction class of deployment stream"""

    @abc.abstractmethod
    def write_title(self, title: str):
        raise NotImplementedError

    @abc.abstractmethod
    def write_message(self, message: str, stream: Optional[StreamType] = None):
        raise NotImplementedError

    @abc.abstractmethod
    def write_event(self, event_name: str, data: dict):
        raise NotImplementedError

    @abc.abstractmethod
    def close(self):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def from_deployment_id(cls, deployment_id: str):
        raise NotImplementedError


class RedisChannelStream(DeployStream):
    """Stream using redis channel"""

    def __init__(self, channel: StreamChannel):
        self.channel = channel

    def write_title(self, title):
        return self.channel.publish(event='title', data=title)

    def write_message(self, message, stream=StreamType.STDOUT):
        return self.channel.publish_msg(message=json.dumps({'line': message, 'stream': str(stream)}))

    def write_event(self, event_name: str, data: dict):
        return self.channel.publish(event=event_name, data=json.dumps(data))

    def close(self):
        return self.channel.close()

    @classmethod
    def from_deployment_id(cls, deployment_id: str) -> 'RedisChannelStream':
        stream_channel = StreamChannel(deployment_id, redis_db=get_default_redis())
        stream_channel.initialize()
        return cls(stream_channel)


class ConsoleStream(DeployStream):
    """Stream using console, useful for unittesting"""

    def write_title(self, title):
        print(f'[TITLE]: {title}')

    def write_message(self, message, stream=StreamType.STDOUT):
        f = sys.stderr if stream == StreamType.STDERR else sys.stdout
        print(message, file=f)

    def write_event(self, event_name: str, data: dict):
        return print(f'[{event_name}: {data}')

    def close(self):
        pass

    @classmethod
    def from_deployment_id(cls, deployment_id: str):
        return cls()


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

        # Only exception `DeployShouldAbortError` or `BadResponse` should be outputed directly into the stream,
        # While other exceptions should be masked as "Unknown error" instead for better user
        # experience.
        if exc_type in [DeployShouldAbortError, BadResponse]:
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


def get_default_stream(deployment: Deployment):
    stream_channel = StreamChannel(deployment.id, redis_db=get_default_redis())
    stream_channel.initialize()
    return RedisChannelStream(stream_channel)


class DeploymentStateMgr:
    """Deployment state manager"""

    def __init__(self, deployment: Deployment, phase_type: 'DeployPhaseTypes', stream: DeployStream = None):
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


class AppDefaultDomains:
    """A helper class for dealing with app's default subdomains during building and releasing"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.engine_app = env.get_engine_app()
        self.engine_client = EngineDeployClient(self.engine_app)

        self.domains: List[Domain] = []
        self.initialize_domains()

    def initialize_domains(self):
        """calculate and store app's default subdomains"""
        region = get_region(self.engine_app.region)
        # get domains only if current region was configured to use "SUBDOMAIN" type entrance
        if region.entrance_config.exposed_url_type == ExposedURLType.SUBDOMAIN:
            # calculate default subdomains
            self.domains = ModuleEnvDomains(self.env).all()

    def sync(self):
        """Sync app's default subdomains to engine"""
        domains = [d.as_dict() for d in self.domains]
        self.engine_client.update_domains(domains)

    def as_env_vars(self) -> Dict:
        """Return current subdomains as env vars"""
        domains_str = ';'.join(d.host for d in self.domains)

        if not domains_str:
            # only if domain exist, would add ENGINE_APP_DEFAULT_SUBDOMAINS key
            return {}

        return {settings.CONFIGVAR_SYSTEM_PREFIX + "ENGINE_APP_DEFAULT_SUBDOMAINS": domains_str}


def get_env_variables(
    env: ModuleEnvironment, include_builtin=True, deployment: Optional[Deployment] = None
) -> Dict[str, str]:
    """Get env vars for current environment, this will includes:

    - env vars from services
    - user defined configvars
    - built-in env vars
    - (optional) vars defined by deployment description file

    :param include_builtin: Whether include builtin config vars
    :param deployment: Optional deployment object to get vars defined in description file
    :returns: Dict of env vars
    """
    result = {}
    engine_app = env.get_engine_app()

    # Part: Gather values from registed env variables providers, it has lowest priority
    result.update(env_vars_providers.gather(env, deployment))

    # Part: system-wide env vars
    if include_builtin:
        result.update(generate_builtin_env_vars(engine_app, settings.CONFIGVAR_SYSTEM_PREFIX))

    # Part: Address for bk_docs_center saas
    # Q: Why not in the generate_builtin_env_vars method？

    # method(get_preallocated_address) and module(ConfigVar) will be referenced circularly
    result.update({'BK_DOCS_URL_PREFIX': get_bk_doc_url_prefix()})

    # Part: insert blobstore env vars
    result.update(generate_blobstore_env_vars(engine_app))

    # Part: user defined env vars
    # Q: Why don't we using engine_app directly to get ConfigVars?
    #
    # Because Config Vars, unlike ServiceInstance, is not bind to EngineApp. It
    # has application global type which shares under every engine_app/environment of an
    # application.
    result.update(get_config_vars(engine_app.env.module, engine_app.env.environment))

    # Part: env vars shared from other modules
    result.update(ServiceSharingManager(env.module).get_env_variables(env))

    # Part: env vars provided by services
    result.update(mixed_service_mgr.get_env_vars(engine_app))

    # Part: Application's default sub domains/paths
    result.update(AppDefaultDomains(env).as_env_vars())
    result.update(AppDefaultSubpaths(env).as_env_vars())
    return result


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


@dataclass
class ServerSendEvent:
    """SSE 事件对象"""

    id: str
    event: str
    data: dict
    __slots__ = ['id', 'event', 'data']

    INTERNAL_TERM: ClassVar[str] = "internal"

    @classmethod
    def from_raw(cls, raw_dict: dict) -> 'ServerSendEvent':
        return cls(
            id=raw_dict['id'],
            event='message' if raw_dict['event'] == 'msg' else raw_dict['event'],
            data=raw_dict['data'],
        )

    @property
    def is_internal(self) -> bool:
        return self.event == self.INTERNAL_TERM

    def to_yield_str_list(self):
        """支持 stream 返回"""
        return ['id: %s\n' % self.id, 'event: %s\n' % self.event, 'data: %s\n\n' % self.data]

    @staticmethod
    def to_eof_str_list():
        """事件流结束标志"""
        return ['id: -1\n', 'event: EOF\n', 'data: \n\n']


@dataclass
class InternalEvent(ServerSendEvent):
    """PaaS 项目内部交互事件，需要遵循特定的事件协议"""

    type: str
    name: str
    status: DeployEventStatus
    publisher: str
    __slots__ = ['type', 'name', 'status', 'publisher']

    UNKNOWN_PUBLISHER_TERM: ClassVar[str] = "unknown"

    @classmethod
    def from_general_event(cls, event: ServerSendEvent) -> 'InternalEvent':
        if not event.is_internal:
            raise InternalEventFormatError("event is not from internal")

        try:
            return InternalEvent(
                id=event.id,
                event=event.event,
                data=event.data,
                name=event.data["name"],
                type=event.data["type"],
                status=DeployEventStatus(event.data["status"]),
                publisher=cls.get_publisher(event.data),
            )
        except KeyError:
            raise InternalEventFormatError("can not load event data via internal format")

    @classmethod
    def get_publisher(cls, data_dict: dict) -> str:
        try:
            return data_dict["publisher"]
        except KeyError:
            return cls.UNKNOWN_PUBLISHER_TERM

    def invoke(self, obj: Union['DeployPhase', 'DeployStepModel'], stream: DeployStream):
        """事件触发，同步更新 DB 记录"""
        obj_job_status = DeployEventStatus.get_job_status(self.status).value
        # 状态相同时不再重复更新
        if obj.status == obj_job_status:
            return

        # step 已经是完成状态了，不再更新
        if obj.is_completed:
            return

        obj.mark_and_write_to_steam(stream=stream, status=JobStatus(obj_job_status))


@dataclass
class InternalEventParser:
    target_publisher: str
    target_event_type: str

    def parse_event(self, raw_event: dict) -> Optional[InternalEvent]:
        """从 Engine 发送的内容中解析 Step 事件, 返回 None 代表无法转换成内部事件"""
        if not raw_event:
            return None

        # 理论上，所有 sse 事件都会被解析
        try:
            event = ServerSendEvent.from_raw(raw_event)
        except Exception:
            logger.exception("Failed to parse SSE event")
            return None

        try:
            event = InternalEvent.from_general_event(event)
        except InternalEventFormatError:
            logger.exception("Malformed SSE internal event")
            return None

        if not event.publisher == self.target_publisher or not event.type == self.target_event_type:
            logger.debug("publisher<%s> is not our target<%s>", event.publisher, self.target_publisher)
            return None

        return event


class MessageParser:
    @classmethod
    def parse_msg(cls, raw_event: dict) -> Optional[ServerSendEvent]:
        """从 SSE 中解析出 msg 字段"""
        if not raw_event:
            return None

        try:
            event = ServerSendEvent.from_raw(raw_event)
        except Exception:
            logger.exception("Failed to parse SSE event")
            return None

        if not event.event == "message":
            return None

        if isinstance(event.data, str):
            event.data = json.loads(event.data)
        return event


class MessageStepMatcher:
    @classmethod
    def match_and_update_step(cls, event: ServerSendEvent, pattern_maps: dict, phase: 'DeployPhase'):
        for job_status, pattern_map in pattern_maps.items():
            for pattern, step_name in pattern_map.items():
                match = re.compile(pattern).findall(event.data['line'])
                # 未能匹配上任何预设匹配集
                if not match:
                    continue

                try:
                    step_obj = phase.get_step_by_name(step_name)
                except StepNotInPresetListError as e:
                    logger.debug("%s, skip", e.message)
                    continue
                except DuplicateNameInSamePhaseError as e:
                    logger.warning("%s, skip", e.message)
                    continue

                # 由于 history events 每次都是重复拉取，所以肯定会重复判断
                if step_obj.status == job_status.value:
                    continue

                # 已经处于完结状态
                if step_obj.is_completed:
                    continue

                logger.info("[%s] going to mark & write to stream", phase.deployment.id)
                # 更新 step 状态，并写到输出流
                step_obj.mark_and_write_to_steam(
                    RedisChannelStream.from_deployment_id(phase.deployment.id), job_status
                )


class AppDefaultSubpaths:
    """A helper class for dealing with app's default subpaths during building and releasing"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.engine_client = EngineDeployClient(env.get_engine_app())
        self.subpaths_service = ModuleEnvSubpaths(self.env)
        self.subpaths = self.subpaths_service.all()

    def sync(self):
        """Sync app's default subpaths to engine"""
        subpaths = [d.as_dict() for d in self.subpaths]
        if subpaths:
            self.engine_client.update_subpaths(subpaths)

    def as_env_vars(self) -> Dict:
        """Return current subpath as env vars"""
        obj = self.subpaths_service.get_shortest()
        if not obj:
            return {}

        return {
            settings.CONFIGVAR_SYSTEM_PREFIX + "SUB_PATH": self._build_sub_path_env(obj),
            settings.CONFIGVAR_SYSTEM_PREFIX + "DEFAULT_SUBPATH_ADDRESS": obj.as_url().as_address(),
        }

    def _build_sub_path_env(self, obj: Subpath):
        # TODO: remove FORCE_USING_LEGACY_SUB_PATH_VAR_VALUE in settings
        if self.env.module.exposed_url_type is None or settings.FORCE_USING_LEGACY_SUB_PATH_VAR_VALUE:
            # reserved for applications with legacy sub-path implementations
            engine_app = self.env.get_engine_app()
            return f"/{engine_app.region}-{engine_app.name}/"
        return obj.subpath
