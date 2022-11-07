# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from django.utils.translation import gettext_lazy as _

from paasng.utils.basic import ChoicesEnum


class OperationType(ChoicesEnum):
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

    OFFLINE_MARKET = 10
    RELEASE_TO_MARKET = 17

    # Deprecated values
    # 以下事件类型已弃用，目前没有任何动作会产生这类事件
    DEPLOY_STAGE = 2
    DEPLOY_PRODUCT = 3
    OFFLINE_APPLICATION_PROD_ENVIRONMENT_WITH_MARKET = 13

    _choices_labels = (
        (CREATE_APPLICATION, _('创建应用')),
        (DEPLOY_STAGE, _('部署预发布环境')),
        (DEPLOY_PRODUCT, _('部署生产环境')),
        (REGISTER_PRODUCT, _('上线并注册到蓝鲸市场')),
        (MODIFY_PRODUCT_ATTRIBUTES, _('完善应用市场配置')),
        (RECYCLE_ONLINE_RESOURCE, _('下线应用服务')),
        (DELETE_APPLICATION, _('删除应用')),
        (OFFLINE_MARKET, _('从应用市场下架')),
        (RELEASE_TO_MARKET, _("发布至应用市场")),
        (OFFLINE_APPLICATION_STAG_ENVIRONMENT, _('下线预发布环境')),
        (OFFLINE_APPLICATION_PROD_ENVIRONMENT, _('下线生产环境')),
        (OFFLINE_APPLICATION_PROD_ENVIRONMENT_WITH_MARKET, _('下线生产环境及蓝鲸市场')),
        (CREATE_MODULE, _("创建模块")),
        (DELETE_MODULE, _("删除模块")),
    )
