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
from typing import Optional
from uuid import UUID

from paas_wl.platform.applications.models.build import Build, BuildProcess
from paas_wl.release_controller.builder.exceptions import InterruptionNotAllowed
from paas_wl.release_controller.builder.executor import interrupt_build
from paas_wl.release_controller.hooks.models import Command
from paas_wl.resources.actions.exec import interrupt_command as _interrupt_command
from paasng.platform.applications.models import ModuleEnvironment


def interrupt_build_proc(bp_id: UUID) -> bool:
    """Interrupt a build process

    :return: Whether the build process was successfully interrupted.
    """
    bp = BuildProcess.objects.get(pk=bp_id)
    if not bp.check_interruption_allowed():
        raise InterruptionNotAllowed()
    return interrupt_build(bp)


def get_latest_build_id(env: ModuleEnvironment) -> Optional[UUID]:
    """Get UUID of the latest build in the given environment

    :return: `None` if no builds can be found
    """
    try:
        return Build.objects.filter(app=env.wl_app).latest('created').pk
    except Build.DoesNotExist:
        return None


def interrupt_command(command_id: UUID) -> bool:
    """Interrupt a command

    :return: Whether the Command was successfully interrupted.
    """
    command = Command.objects.get(pk=command_id)
    if not command.check_interruption_allowed():
        raise InterruptionNotAllowed
    return _interrupt_command(command)
