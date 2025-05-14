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

# providing_args: [value: str]
prepare_use_application_code = Signal()

# providing_args: [value: str, instance: Optional["Application"] = None]
prepare_use_application_name = Signal()

# providing_args: [application: Application]
post_create_application = Signal()

# providing_args: [application: Application]
before_finishing_application_creation = Signal()

# providing_args: [code: str, name: Optional[str] = None, name_en: Optional[str] = None]
prepare_change_application_name = Signal()

# providing_args: [offline_instance: OfflineOperation, environment: str]
module_environment_offline_success = Signal()

# providing_args: [application: Application]
application_member_updated = Signal()

# providing_args: [application: Application, new_module: Module, old_module: Module]
application_default_module_switch = Signal()

# Signal that represents an update of application's logo, make sure to send this signal when logo was updated.
# providing_args: [application: Application]
application_logo_updated = Signal()
