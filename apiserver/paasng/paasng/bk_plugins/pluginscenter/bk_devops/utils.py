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


def get_devops_project_id(git_project_id: int) -> str:
    """获取工蜂仓库对应的蓝盾项目ID, 用于获取仓库的代码检查等信息

    :param git_project_id: 工蜂仓库项目ID
    :return: 蓝盾项目ID
    """
    # 仓库对应的蓝盾项目ID为: 在工蜂项目ID前添加 git_ 前缀
    return f"git_{git_project_id}"
