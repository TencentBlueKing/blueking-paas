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
    """网关申请记录 取消/删除 操作失败

    :param message: 网关返回的错误信息, 可能为空
    :param status_code: 网关返回的 HTTP 状态码, 网络异常等场景下为空
    :param gateway_error_code: 网关层错误码 (如 APP_NO_PERMISSION)
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
    def from_gateway_exception(cls, exc: Exception) -> "ApplyRecordOperateError":
        """根据网关请求异常构造, 自动提取状态码, 错误信息与网关层错误码"""
        status_code, message = extract_gateway_error(exc)
        # 网关层错误 (应用认证, 资源授权失败等) 由响应头标记, 此时请求未到达业务后端
        gateway_error_code = str(getattr(exc, "error_code", "") or "")
        return cls(message=message, status_code=status_code, gateway_error_code=gateway_error_code)


def extract_gateway_error(exc: Exception) -> tuple[int | None, str]:
    """从网关请求异常中提取 (status_code, message)

    优先取响应体中error.message, 其次兼容 DRF 风格的 detail/message, 最后回退到原始响应文本.
    """
    status_code = getattr(exc, "response_status_code", None)

    body = None
    response_json = getattr(exc, "response_json", None)
    if callable(response_json):
        try:
            body = response_json()
        except Exception:  # noqa: BLE001 - 响应体可能不是合法的 JSON
            body = None

    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("message"):
            return status_code, str(error["message"])
        for key in ("detail", "message"):
            if body.get(key):
                return status_code, str(body[key])

    # 兜底: 使用原始响应文本, 避免错误信息过长
    response_text = getattr(exc, "response_text", "") or ""
    return status_code, str(response_text)[:500] or str(exc)


# 网关返回的错误信息中表示 "接口未注册" 的关键字
_API_NOT_FOUND_MARKERS = ("API not found",)


def _to_api_error(exc: ApplyRecordOperateError) -> APIError:
    """将网关异常转换为 PaaS 的统一错误"""
    # 网关层拒绝时请求不会到达业务后端, 需与业务层的 "记录不存在" 区分开, 否则会误导排查方向.
    # 两者的处置方式不同: 接口未注册需发布并同步网关资源, 未授权则需在网关上为调用方授权资源
    if exc.gateway_error_code:
        if any(marker in exc.message for marker in _API_NOT_FOUND_MARKERS):
            return error_codes.CLOUD_API_GATEWAY_API_NOT_REGISTERED

        return error_codes.CLOUD_API_GATEWAY_PERMISSION_DENIED

    if exc.status_code == 404:
        # 记录不存在, 不属于当前应用或不在当前租户范围内, 网关不区分这几种场景
        return error_codes.CLOUD_API_APPLY_RECORD_NOT_FOUND

    if exc.status_code == 400:
        # 状态不合法 (如非待审批的申请被取消) 等业务错误, 透传网关返回的信息
        if exc.message:
            return error_codes.CLOUD_API_APPLY_RECORD_STATUS_INVALID.f(exc.message, replace=True)
        return error_codes.CLOUD_API_APPLY_RECORD_STATUS_INVALID

    # 其余情况 (500/502/503, 网络异常等) 统一提示服务暂不可用
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
