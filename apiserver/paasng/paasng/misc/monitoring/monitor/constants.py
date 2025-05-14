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

###########
# 消息模板 #
###########
TITLE = "【蓝鲸PaaS】应用 {{ app_code }} 内 {{ proc_name }} 进程运行异常通知"
BASE_MESSAGE_TEMPLATE = """
{% if mail -%}<pre>{% endif %}
应用名称:   {{app_name}}
应用ID:   {{app_code}}
应用环境:   {{app_env}}
异常进程:   {{proc_name}}

"""

ABNORMAL_APP_MESSAGE_TEMPLATE = (
    BASE_MESSAGE_TEMPLATE
    + """
应用运行异常，请及时查看<a href="{{bkpaas_url}}/developer-center/apps/{{app_code}}/process">异常日志</a>并进行修复异常！
{% if mail -%}</pre>{% endif %}
"""
)

SCALE_DOWN_APP_MESSAGE_TEMPLATE = (
    BASE_MESSAGE_TEMPLATE
    + """
应用<{{app_name}}>重启次数过多，为了不影响平台稳定性，该进程实例副本已被缩减为0，请
<a href="{{bkpaas_url}}/developer-center/apps/{{app_code}}/process">查看详情</a>了解异常原因。在修复异常后，重新部署应用即可
{% if mail -%}</pre>{% endif %}
"""
)

##############
# 缩容相关阈值 #
##############
# instance age threshold is 30 min
APP_INSTANCE_AGE_THRESHOLD = 30
# empirical value
RESTART_COUNT_THRESHOLD = 20
