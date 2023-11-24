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

from enum import Enum

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _

from paasng.core.region.states import RegionType


class ProductSourceUrlType(int, StructuredEnum):
    """访问地址类型"""

    DISABLED = EnumField(1, label="未开启")
    ENGINE_PROD_ENV = EnumField(2, label="与绑定模块生产环境一致")
    THIRD_PARTY = EnumField(3, label="第三方访问地址")
    CUSTOM_DOMAIN = EnumField(4, label="绑定模块生产环境独立域名")
    ENGINE_PROD_ENV_HTTPS = EnumField(5, label="与绑定模块生产环境一致, 并启用 HTTPS")


class AppType(Enum):
    """应用分类（按实现技术）"""

    PAAS_APP = 1  # 基于BK PAAS服务构建的应用
    THIRD_PARTY = 2  # 以独立链接的形式展示在桌面

    _choices_labels = ((PAAS_APP, "蓝鲸应用"), (THIRD_PARTY, "第三方应用"))

    @classmethod
    def get_choices(cls):
        return cls._choices_labels.value


class AppState(Enum):
    """应用市场中应用的状态"""

    DEVELOPING = 1  # 开发中
    RELEASED = 2  # 已发布
    OFFLINE = 3  # 市场下架

    _choices_labels = ((DEVELOPING, "开发中"), (RELEASED, "已发布"), (OFFLINE, "市场下架"))

    @classmethod
    def get_choices(cls):
        return cls._choices_labels.value


TAG_REGION_CHOICES = list(RegionType.get_choices()) + [("all", "所有版本")]


class OpenMode(str, StructuredEnum):
    """应用在桌面的打开方式"""

    DESKTOP = EnumField(real_value="desktop", label="桌面")
    NEW_TAB = EnumField(real_value="new_tab", label="新标签页")


class TagName(str, StructuredEnum):
    """应用分类名称"""

    OPSTOOlS = EnumField("OpsTools", label=_("运维工具"))
    MONITORAlARM = EnumField("MonitorAlarm", label=_("监控告警"))
    CONFMANAGE = EnumField("ConfManage", label=_("配置管理"))
    DEVTOOLS = EnumField("DevTools", label=_("开发工具"))
    ENTERPRISEIT = EnumField("EnterpriseIT", label=_("企业IT"))
    OFFICEAPP = EnumField("OfficeApp", label=_("办公应用"))
    OTHER = EnumField("Other", label=_("其它"))
