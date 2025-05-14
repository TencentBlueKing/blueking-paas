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

from django.dispatch import Signal

# Triggered when a single deployment process is finished(usually in background worker process)
# providing_args: [deployment: Deployment]
post_appenv_deploy = Signal()

# providing_args: [deployment: Deployment]
pre_appenv_deploy = Signal()

# TODO 这个信号应该没有用到？（sent but not receiver）
# providing_args: [deployment: Deployment, step: DeployStep]
pre_appenv_build = Signal()

# mainly for DeployPhase & DeployStep
# providing_args: [phase: DeployPhaseTypes]
pre_phase_start = Signal()

# providing_args: [status: JobStatus, phase: DeployPhaseTypes]
post_phase_end = Signal()

# triggered when module_env released
# providing_args: [env: ModuleEnvironment]
on_release_created = Signal()

# providing_args: [events: Iterable[ProcessBaseEvent], extra_params: Dict]
processes_updated = Signal()
