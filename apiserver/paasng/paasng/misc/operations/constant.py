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

from django.utils.translation import gettext_lazy as _

from paasng.utils.basic import ChoicesEnum


class OperationType(ChoicesEnum):
    """[deprecated] 请不要再使用 misc.operations 目录下的任何内容，暂时保留仅用于社区版本将存量的操作记录同步到 misc.audit 中"""

    CREATE_APPLICATION = 1
    REGISTER_PRODUCT = 4
    MODIFY_PRODUCT_ATTRIBUTES = 5
    PROCESS_START = 6
    PROCESS_STOP = 7
    RECYCLE_ONLINE_RESOURCE = 8
    DELETE_APPLICATION = 9

    OFFLINE_APPLICATION_STAG_ENVIRONMENT = 11
    OFFLINE_APPLICATION_PROD_ENVIRONMENT = 12

    DEPLOY_APPLICATION = 14
    CREATE_MODULE = 15
    DELETE_MODULE = 16
    DEPLOY_CNATIVE_APP = 17

    OFFLINE_MARKET = 10
    RELEASE_TO_MARKET = 17

    # 云 API 权限申请相关
    APPLY_PERM_FOR_CLOUD_API = 21
    RENEW_PERM_FOR_CLOUD_API = 22

    # 白名单访问相关
    ENABLE_ACCESS_CONTROL = 23
    DISABLE_ACCESS_CONTROL = 24

    # Deprecated 以下事件类型已弃用，目前没有任何动作会产生这类事件
    DEPLOY_STAGE = 2
    DEPLOY_PRODUCT = 3
    OFFLINE_APPLICATION_PROD_ENVIRONMENT_WITH_MARKET = 13

    _choices_labels = (
        (CREATE_APPLICATION, _("创建应用")),
        (DEPLOY_STAGE, _("部署预发布环境")),
        (DEPLOY_PRODUCT, _("部署生产环境")),
        (REGISTER_PRODUCT, _("上线并注册到蓝鲸市场")),
        (MODIFY_PRODUCT_ATTRIBUTES, _("完善应用市场配置")),
        (RECYCLE_ONLINE_RESOURCE, _("下线应用服务")),
        (DELETE_APPLICATION, _("删除应用")),
        (OFFLINE_MARKET, _("从应用市场下架")),
        (RELEASE_TO_MARKET, _("发布至应用市场")),
        (OFFLINE_APPLICATION_STAG_ENVIRONMENT, _("下线预发布环境")),
        (OFFLINE_APPLICATION_PROD_ENVIRONMENT, _("下线生产环境")),
        (OFFLINE_APPLICATION_PROD_ENVIRONMENT_WITH_MARKET, _("下线生产环境及蓝鲸市场")),
        (CREATE_MODULE, _("创建模块")),
        (DELETE_MODULE, _("删除模块")),
        (APPLY_PERM_FOR_CLOUD_API, _("申请网关 API 权限")),
        (RENEW_PERM_FOR_CLOUD_API, _("续期网关 API 权限")),
        (ENABLE_ACCESS_CONTROL, _("开启用户访问限制")),
        (DISABLE_ACCESS_CONTROL, _("关闭用户访问限制")),
    )
