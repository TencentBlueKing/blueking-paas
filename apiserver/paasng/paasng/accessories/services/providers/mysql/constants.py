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
from blue_krill.data_types.enum import IntStructuredEnum


class MySQLAuthTypeEnum(IntStructuredEnum):
    GRANT = 1
    REVOKE = 2


GRANT_SQL_FMT = 'grant all privileges on `{db_name}`.* to `{db_user}`@`{auth_ip}` identified by "{db_password}";'

REVOKE_SQL_FMT = "revoke all privileges on `{db_name}`.* from `{db_user}`@{auth_ip};"
