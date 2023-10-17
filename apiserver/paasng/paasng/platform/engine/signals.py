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
from django.dispatch import Signal

# Triggered when a single deployment process is finished(usually in background worker process)
post_appenv_deploy = Signal(providing_args=['deployment'])
pre_appenv_deploy = Signal(providing_args=['deployment'])
pre_appenv_build = Signal(providing_args=['deployment', 'step'])

# mainly for DeployPhase & DeployStep
pre_phase_start = Signal(providing_args=['phase'])
post_phase_end = Signal(providing_args=['status', 'phase'])

# 当某个 module_env 进行 release 时, 会触发该信号
on_release_created = Signal(providing_args=["env"])

processes_updated = Signal(providing_args=['events', 'extra_params'])
