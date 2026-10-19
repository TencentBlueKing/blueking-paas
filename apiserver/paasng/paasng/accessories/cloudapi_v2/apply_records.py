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

"""云 API 权限申请记录 取消/删除 的公共逻辑

网关 (bk-apigateway) 的取消, 删除接口在状态不合法, 记录不存在等场景下会返回
{"error": {"code": ..., "message": ...}} 格式的错误响应, 本模块负责将其转换为
PaaS 统一的错误响应, 并记录应用的审计信息.
"""

import logging
from contextlib import contextmanager
from typing import Iterator

from blue_krill.web.std_error import APIError

from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)

# 网关 operated_by 字段的长度限制, 超长会导致网关拒绝请求
OPERATED_BY_MAX_LENGTH = 32


class ApplyRecordOperateError(Exception):
    """网关 取消/删除 申请记录失败

    保留网关的状态码与错误信息, 供转换为 PaaS 统一错误时区分 "记录不存在", "状态不合法" 等场景.

    :param message: 网关返回的错误信息, 可能为空
    :param status_code: 网关返回的 HTTP 状态码, 网络异常等场景下为空
    :param gateway_error_code: 网关层错误码, 由响应头标记
    """

    def __init__(
        self,
        message: str = "",
        status_code: int | None = None,
        gateway_error_code: str = "",
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.gateway_error_code = gateway_error_code

    @classmethod
    def from_exception(cls, exc: Exception) -> "ApplyRecordOperateError":
        """从网关请求异常构造, 提取状态码, 错误信息与网关层错误码"""
        status_code = getattr(exc, "response_status_code", None)
        # 网关层错误 (应用认证, 资源授权失败等) 由响应头标记, 此时请求未到达业务后端
        gateway_error_code = str(getattr(exc, "error_code", "") or "")

        body = None
        response_json = getattr(exc, "response_json", None)
        if callable(response_json):
            try:
                body = response_json()
            except ValueError:
                body = None

        # 网关业务错误固定返回 {"error": {"code": ..., "message": ...}}
        error = body.get("error") if isinstance(body, dict) else None
        message = str(error.get("message") or "") if isinstance(error, dict) else ""

        return cls(message=message, status_code=status_code, gateway_error_code=gateway_error_code)


def _to_api_error(exc: ApplyRecordOperateError) -> APIError:
    """将网关异常转换为 PaaS 的统一错误"""
    if not exc.gateway_error_code:
        if exc.status_code == 404:
            return error_codes.CLOUD_API_APPLY_RECORD_NOT_FOUND

        if exc.status_code == 400:
            if exc.message:
                return error_codes.CLOUD_API_APPLY_RECORD_STATUS_INVALID.f(exc.message, replace=True)
            return error_codes.CLOUD_API_APPLY_RECORD_STATUS_INVALID

    return error_codes.CLOUD_API_SERVICE_UNAVAILABLE


@contextmanager
def handle_apply_record_operate_error() -> Iterator[None]:
    """将网关返回的错误转换为 PaaS 的统一错误响应"""
    try:
        yield
    except ApplyRecordOperateError as e:
        # 取消/删除 失败属于低频且需排查的场景, 统一记录完整上下文, 避免仅凭状态码误判
        logger.warning(
            "Operate apply record failed, status_code: %s, gateway_error_code: %s, message: %s",
            e.status_code,
            e.gateway_error_code or "-",
            e.message,
            exc_info=not e.status_code,
        )
        raise _to_api_error(e) from e


def validate_operated_by(operated_by: str) -> str:
    """校验 operated_by 是否符合网关的约束 (非空且不超过 32 个字符)

    :return: 校验通过的 operated_by
    """
    if not operated_by or not operated_by.strip() or len(operated_by) > OPERATED_BY_MAX_LENGTH:
        raise error_codes.CLOUD_API_OPERATED_BY_INVALID
    return operated_by


def add_operate_audit_record(
    *,
    app_code: str,
    tenant_id: str,
    user: str,
    operation: OperationEnum,
    record_id: int,
    gateway_name: str = "",
    detail_data: str | int | dict | list | None = None,
) -> None:
    """记录申请记录取消/删除的审计信息

    :param app_code: 应用 ID, 即操作所属的应用
    :param user: encode 后的用户名, 即 request.user.pk
    :param operation: 操作类型, 取消或删除
    :param record_id: 申请记录 ID, 用于审计追溯
    :param gateway_name: 网关名称, 用于审计追溯
    :param detail_data: 记录在审计中的详情数据. DataType.CLOUD_API_RECORD + 申请记录 ID 时.
        操作记录页面会提供 "查看详情" 入口并通过 ID 查询单据详情; 若单据已不可查询 (如已删除的申请,
        MCP Server 申请), 应传入字典以避免展示无效的详情入口.
    """
    if detail_data is None:
        detail_data = record_id

    try:
        add_app_audit_record(
            app_code=app_code,
            tenant_id=tenant_id,
            user=user,
            action_id=AppAction.MANAGE_CLOUD_API,
            operation=operation,
            target=OperationTarget.CLOUD_API,
            attribute=gateway_name,
            result_code=ResultCode.SUCCESS,
            data_after=DataDetail(type=DataType.CLOUD_API_RECORD, data=detail_data),
        )
    except Exception:
        logger.exception("Failed to add audit record for operate apply record")
