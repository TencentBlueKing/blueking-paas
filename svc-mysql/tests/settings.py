# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import os

# 在导入正式 settings 之前补上测试默认值。正式进程不会走这个模块。
os.environ.setdefault("PAAS_SERVICE_JWT_CLIENTS_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/svc-mysql-pytest.sqlite3")

from svc_mysql.settings import *
