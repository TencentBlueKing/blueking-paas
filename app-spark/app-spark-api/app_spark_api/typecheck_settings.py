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

"""mypy 专用的 settings shim。

真实 settings 模块要求 `BKKRILL_ENCRYPT_SECRET_KEY` 必须存在（见
`app_spark_api.settings` 中的 `Validator(must_exist=True)`），因为生产进程没有这条退路。
但 mypy 的 django-stubs 插件会 import settings 来 introspect 模型，此上下文里没有
YAML / 环境变量，校验会直接让 typecheck 崩溃。

这个模块先塞一个一次性的 key，再重新导出真实 settings，从而让 typecheck 无需任何配置即可
运行。它只被 `[tool.django-stubs] django_settings_module` 引用，生产进程的
`DJANGO_SETTINGS_MODULE` 仍指向 `app_spark_api.settings`，永远不会 import 到这里。
"""

import os

os.environ.setdefault(
    "APP_SPARK_API_BKKRILL_ENCRYPT_SECRET_KEY",
    "Q3NyY0V3cFpTUlVNbHp3RUZMYWtXaEdOdXp3eWZNSkc=",
)

from app_spark_api.settings import *
