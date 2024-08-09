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

import django.dispatch

prepare_use_application_code = django.dispatch.Signal(providing_args=["value"])
prepare_use_application_name = django.dispatch.Signal(providing_args=["value", "instance"])
post_create_application = django.dispatch.Signal(providing_args=["application"])
before_finishing_application_creation = django.dispatch.Signal(providing_args=["application"])

prepare_change_application_name = django.dispatch.Signal(providing_args=["region", "code", "name", "name_en"])


module_environment_offline_success = django.dispatch.Signal(providing_args=["offline_instance", "environment"])
application_member_updated = django.dispatch.Signal(providing_args=["application"])

application_default_module_switch = django.dispatch.Signal(providing_args=["application", "new_module", "old_module"])

# Signal that represents an update of application's logo, make sure to send this signal when logo
# was updated.
application_logo_updated = django.dispatch.Signal(providing_args=["application"])
