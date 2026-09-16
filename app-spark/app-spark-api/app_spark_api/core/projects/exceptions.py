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

"""Project 相关的失败。"""


class ProjectConflictError(Exception):
    """要创建的 Project 和已有数据撞上了。

    分成下面两个子类，是因为调用方要做的事不一样：撞 ID 换个 ID 就行，撞名字得换名字。只给一个
    「已存在」会把这个判断推给调用方去猜。
    """


class ProjectIdTakenError(ProjectConflictError):
    """这个 Project ID 已经被占用了。ID 是全局唯一的，不分租户。"""


class ProjectNameTakenError(ProjectConflictError):
    """同租户下已经有同名 Project 了。"""
