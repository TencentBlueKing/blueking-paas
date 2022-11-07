# -*- coding: utf-8 -*-
import datetime
import json
import logging
from typing import Dict, Optional

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.platform.applications.constants import AppOperationType, EngineAppType
from paas_wl.platform.applications.models import EngineApp
from paas_wl.platform.applications.permissions import application_perm_class
from paas_wl.platform.applications.views import ApplicationCodeInPathMixin
from paas_wl.platform.auth.views import BaseEndUserViewSet
from paas_wl.platform.external.client import get_plat_client
from paas_wl.platform.external.exceptions import PlatClientRequestError
from paas_wl.platform.system_api.serializers import ProcExtraInfoSLZ, ProcSpecsSerializer
from paas_wl.resources.actions.exceptions import ScaleFailedException
from paas_wl.utils.error_codes import error_codes
from paas_wl.utils.views import IgnoreClientContentNegotiation
from paas_wl.workloads.processes.constants import ProcessUpdateType
from paas_wl.workloads.processes.controllers import AppProcessesController, judge_operation_frequent
from paas_wl.workloads.processes.drf_serializers import (
    InstanceForDisplaySLZ,
    ListProcessesSLZ,
    ProcessSpecSLZ,
    UpdateProcessSLZ,
    WatchProcessesSLZ,
)
from paas_wl.workloads.processes.exceptions import ProcessOperationTooOften
from paas_wl.workloads.processes.managers import AppProcessManager
from paas_wl.workloads.processes.models import Instance, ProcessSpec
from paas_wl.workloads.processes.readers import instance_kmodel, process_kmodel
from paas_wl.workloads.processes.watch import watch_process_events

logger = logging.getLogger(__name__)


class ProcessesViewSet(BaseEndUserViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class('manage_processes')]

    _operation_interval: datetime.timedelta = datetime.timedelta(seconds=3)
    _skip_judge_frequent: bool = False

    def update(self, request, code, module_name, environment):
        """操作进程，支持的操作：启动、停止、调整时实例数"""
        slz = UpdateProcessSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        module_env = self.get_module_env_via_path()
        if module_env.is_offlined:
            logger.warning("Unable to update process, environment %s has gone offline.", module_env)
            raise error_codes.CANNOT_OPERATE_PROCESS.f('环境已下架')

        engine_app = self.get_engine_app_via_path()
        ctl = AppProcessesController(engine_app)

        process_spec = self.get_object(data["process_type"])
        judge_operation_frequent(process_spec, self._operation_interval)
        try:
            if data['operate_type'] == ProcessUpdateType.SCALE:
                ctl.scale(process_spec, data['target_replicas'])
            elif data['operate_type'] == ProcessUpdateType.STOP:
                ctl.stop(process_spec)
            elif data['operate_type'] == ProcessUpdateType.START:
                ctl.start(process_spec)
            else:
                raise error_codes.PROCESS_OPERATE_FAILED.f(f"Invalid operate type {data['operate_type']}")
        except ProcessOperationTooOften as e:
            raise error_codes.PROCESS_OPERATION_TOO_OFTEN.f(str(e), replace=True)
        except ScaleFailedException as e:
            raise error_codes.PROCESS_OPERATE_FAILED.f(str(e), replace=True)

        # Create application operation log
        op_type = self.get_logging_operate_type(data['operate_type'])
        if op_type:
            try:
                module = self.get_module_via_path()
                get_plat_client().create_operation_log(
                    application_id=str(module.application_id),
                    operate_type=op_type,
                    operator=request.user.pk,
                    source_object_id=str(module_env.id),
                    module_name=module.name,
                    extra_values={"process_type": data['process_type'], "env_name": module_env.environment},
                )
            except PlatClientRequestError:
                logger.exception('Error creating app operation log')

        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def get_logging_operate_type(type_: str) -> Optional[int]:
        """Get the type of application operation"""
        return {'start': AppOperationType.PROCESS_START, 'stop': AppOperationType.PROCESS_STOP}.get(type_, None)

    def get_object(self, process_type: str):
        engine_app = self.get_engine_app_via_path()
        try:
            return ProcessSpec.objects.get(engine_app_id=engine_app.uuid, name=process_type)
        except ProcessSpec.DoesNotExist:
            raise error_codes.PROCESS_OPERATE_FAILED.f(f"进程 '{process_type}' 未定义")


class ListAndWatchProcsViewSet(BaseEndUserViewSet, ApplicationCodeInPathMixin):

    permission_classes = [IsAuthenticated, application_perm_class('manage_processes')]

    # Use special negotiation class to accept "text/event-stream" content type
    content_negotiation_class = IgnoreClientContentNegotiation

    def list(self, request, code, module_name, environment):
        """获取当前进程与进程实例，支持通过 release_id 参数过滤结果"""
        engine_app = self.get_engine_app_via_path()
        serializer = ListProcessesSLZ(data=request.query_params, context={'engine_app': engine_app})
        serializer.is_valid(raise_exception=True)

        data = get_proc_insts(engine_app, release_id=serializer.validated_data['release_id'])

        # Attach ProcessSpec related data
        packages = ProcessSpec.objects.filter(engine_app=engine_app).select_related('plan')
        data['process_packages'] = ProcessSpecSLZ(packages, many=True).data
        return Response(data)

    def watch(self, request, code, module_name, environment):
        """实时监听进程与进程实例变动情况"""
        engine_app = self.get_engine_app_via_path()
        serializer = WatchProcessesSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        def resp():
            logger.debug('Start watching process, app=%s, params=%s', engine_app.name, dict(data))
            stream = watch_process_events(
                engine_app,
                timeout_seconds=data['timeout_seconds'],
                rv_proc=data['rv_proc'],
                rv_inst=data['rv_inst'],
            )
            for event in stream:
                event = self.process_event(engine_app, event)
                yield 'event: message\n'
                yield 'data: {}\n\n'.format(json.dumps(event))

            yield 'id: -1\n'
            yield 'event: EOF\n'
            yield 'data: \n\n'
            logger.info('Watching finished, app=%s, params=%s', engine_app.name, dict(data))

        return StreamingHttpResponse(resp(), content_type='text/event-stream')

    @staticmethod
    def process_event(engine_app: EngineApp, event: Dict) -> Dict:
        """Process event payload, modifies original event"""
        payload = event['object']
        # Replace instance events with fewer fields
        if event['object_type'] == 'instance':
            event['object'] = InstanceForDisplaySLZ(Instance(app=engine_app, **payload)).data
        return event


def get_proc_insts(engine_app: EngineApp, release_id: Optional[str] = None) -> Dict:
    """Build a structured data including processes and instances

    :param release_id: if given, include instances created by given release only
    :return: A dict with "processes" and "instances"
    """
    procs = process_kmodel.list_by_app_with_meta(app=engine_app)
    procs_items = ProcSpecsSerializer(procs.items, many=True)

    insts = instance_kmodel.list_by_app_with_meta(app=engine_app)
    insts_items = InstanceForDisplaySLZ(insts.items, many=True)

    # Filter instances if required
    insts_data = insts_items.data
    if release_id:
        release = engine_app.release_set.get(pk=release_id)
        insts_data = [inst for inst in insts_data if inst['version'] == str(release.version)]

    # Get extra infos
    proc_extra_infos = []
    if engine_app.type != EngineAppType.CLOUD_NATIVE:
        for proc_spec in procs.items:
            release = engine_app.release_set.get(version=proc_spec.version)
            process_obj = AppProcessManager(app=engine_app).assemble_process(proc_spec.name, release=release)
            proc_extra_infos.append(ProcExtraInfoSLZ(process_obj).data)

    return {
        'processes': {
            'items': procs_items.data,
            'extra_infos': proc_extra_infos,
            'metadata': {'resource_version': procs.get_resource_version()},
        },
        'instances': {
            'items': insts_data,
            'metadata': {'resource_version': insts.get_resource_version()},
        },
    }
