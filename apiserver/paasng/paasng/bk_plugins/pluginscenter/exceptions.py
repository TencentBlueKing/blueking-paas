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
from blue_krill.web.std_error import ErrorCode
from django.utils.translation import gettext_lazy as _


class ErrorCodes:
    CREATE_REPO_ERROR = ErrorCode(_("创建插件项目(源码)失败, 请联系管理员"))
    INITIAL_REPO_ERROR = ErrorCode(_("初始化项目代码失败, 请联系管理员"))
    THIRD_PARTY_API_ERROR = ErrorCode(_("插件后台系统异常, 请联系管理员"))
    DELETE_REPO_ERROR = ErrorCode(_("删除插件项目(源码)失败, 请联系管理员"))

    CANNOT_RELEASE_DUPLICATE_SOURCE_VERSION = ErrorCode(_("该代码分支/Tag 已经发布过，不能重复发布"))
    CANNOT_RELEASE_ONGOING_EXISTS = ErrorCode(_("已有发布任务进行中，请刷新查看"))
    CANNOT_RERUN_ONGOING_STEPS = ErrorCode(_("重试步骤失败, 当前步骤不支持重试。"))
    CANNOT_ROLLBACK_CURRENT_STEP = ErrorCode(_("无法退回至上一步"))
    CANNOT_CANCEL_RELEASE = ErrorCode(_("无法停止发布"))
    NOT_SUPPORT_CANCEL_RELEASE = ErrorCode(_("插件不支持终止发布操作"))
    CANNOT_RESET_RELEASE = ErrorCode(_("无法重新发布该版本"))
    EXECUTE_STAGE_ERROR = ErrorCode(_("发布步骤执行失败"))
    STAGE_DEF_NOT_FOUND = ErrorCode(_("当前步骤在新的发布流程中被移除, 请重新发起部署流程或联系插件管理员"))
    CONFIGURATION_CONFLICT = ErrorCode(_("该插件 {conflict_fields} 的配置项已存在, 不能重复添加"))
    STAGE_RENDER_ERROR = ErrorCode(_("查询步骤详情失败"))
    # 人员管理
    MEMBERSHIP_DELETE_FAILED = ErrorCode(_('插件应该至少拥有一个管理员'))
    MEMBERSHIP_ADD_FAILED = ErrorCode(_("添加插件成员失败"))
    MEMBERSHIP_UPDATE_FAILED = ErrorCode(_("修改插件成员角色失败"))
    # 下架或删除插件相关
    CANNOT_BE_DELETED = ErrorCode(_('不允许删除'))
    PLUGIN_ARCHIVED = ErrorCode(_("插件已下架, 无法进行该操作"))
    # 插件仓库成员管理异常
    MAINTAIN_REPO_MEMBERS_ERROR = ErrorCode(_("添加/删除仓库成员异常, 请稍后重试"))
    # 获取仓库概览数据异常
    QUERY_REPO_OVERVIEW_DATA_ERROR = ErrorCode(_("查询代码仓库概览数据异常"))
    # 日志查询异常
    QUERY_ES_ERROR = ErrorCode(_("日志系统异常, 请稍后重试"))

    def dump(self, fh=None):
        """A function to dump ErrorCodes as markdown table."""
        attrs = [attr for attr in dir(self) if attr.isupper()]
        table = {}
        for attr in attrs:
            code = getattr(self, attr)
            if code.code_num == -1:
                continue
            table[code.code_num] = code.message

        print(_("| 错误码 | 描述 |"), file=fh)
        print("| - | - |", file=fh)
        for code_num, message in sorted(table.items()):
            print(f"| {code_num} | {message} |", file=fh)


error_codes = ErrorCodes()
