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
#
"""A package that helps manage API permissions.

---

perm_insure 模块的主要功能是确保每一个视图函数都配置了恰当的权限要求，它的工作原理是逐个
扫描每一个视图函数，确保其符合以下条件：

- 对于 DRF 视图，确保类级别的 permission_classes 配置了除 IsAuthenticated 之外的权限类
    - （视图内部代码是否调用 check_object_permission 暂时无法确保）
- 或视图方法本身使用了 @site_perm_required 或 @permission_classes 装饰器来独立配置权限
    - （所设置的具体权限是否合理，暂时无法确保）

对于那些无法满足以上要求的视图函数（如只使用 basic-auth 认证的 metrics 接口），则需要修改
本模块的 conf.INSURE_CHECKING_EXCLUDED_VIEWS 配置项，将“视图”或“视图+方法”名显式添加到其中，
否则项目将无法启动。

综上所述，perm_insure 通过增加对权限配置的二次确认，来规避权限配置错误。
"""

default_app_config = "paasng.infras.perm_insure.apps.PermInsureConfig"
