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
import logging
from typing import Optional, Type

from blue_krill.web.std_error import APIError
from django.utils.translation import gettext as _
from rest_framework.exceptions import ErrorDetail, ValidationError

from paasng.accessories.servicehub.remote.exceptions import GetClusterEgressInfoError
from paasng.accessories.services.exceptions import ResourceNotEnoughError
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


def wrap_validation_error(exc: ValidationError, parent: str) -> ValidationError:
    """Wraps a `ValidationError` object, change the error detail to include a parent field. when
    `exc.detail` is a dict, insert the parent field to all field names, otherwise prepend an
    identifier string which contains the name of parent field to all error messages.

    This function is made for flatten error details, errors in nested and complex structure are
    not supported.

    :param parent: The parent field name to be prepend.
    """
    if isinstance(exc.detail, list):
        details = []
        for data in exc.detail:
            if isinstance(data, str):
                # Preserve the "code" attribute
                code = getattr(data, 'code', ValidationError.default_code)
                details.append(ErrorDetail(f'[{parent}] {data}', code))
            else:
                details.append(data)
        return ValidationError(detail=details)
    elif isinstance(exc.detail, dict):
        return ValidationError(detail={parent: exc.detail})
    raise RuntimeError('The type of detail is invalid')


def find_innermost_exception(exception: BaseException) -> BaseException:
    """find the innermost exception in the exception chain."""
    if exception.__cause__ is not None:
        return find_innermost_exception(exception.__cause__)
    return exception


def detect_error_code(exception_cls: Type[BaseException]) -> Optional[APIError]:
    if exception_cls == GetClusterEgressInfoError:
        return error_codes.CANNOT_GET_CLUSTER_INFO
    if exception_cls == ResourceNotEnoughError:
        return error_codes.RESOURCE_POOL_IS_EMPTY

    logger.warning("Can't get error code from Exception<%s>", exception_cls)
    return None


def find_coded_error_message(exception: BaseException) -> Optional[str]:
    """Turn a Exception into bk error code and error message.
    # Q: 为什么需要将一个异常转换成 error_codes 中定义的编码好的异常呢?
    # A: 根据约定, error_codes 异常只会在与前端交互的接口中使用, 其他地方不直接使用 error_codes.
         因此, 在部署过程中需要给用户暴露异常细节时, 则需要使用该 API 获取对应的异常信息, 并直接在前端中展示.

    """
    # Q: 为什么关注异常堆栈最底部的异常?
    # A: 因为异常堆栈最底部的异常才是真正导致报错的异常.
    if not issubclass(type(exception), Exception):
        raise ValueError(f"Expect Type[Exception], but got {type(exception)}")

    exception = find_innermost_exception(exception)
    coded_error = detect_error_code(type(exception))
    if coded_error is None:
        return None

    message = _("错误码: {code_num}, {msg}").format(
        code_num=coded_error.code_num, msg=coded_error.format(str(exception)).message
    )
    # 保证 message 以句号"。"结尾, 但是又不会出现多个句号结尾。
    return message.rstrip(".。") + "。"
