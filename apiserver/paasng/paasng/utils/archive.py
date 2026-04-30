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

"""安全解压归档文件的工具

提供 `safe_extract_zip` 函数, 用于安全地解压 ZIP 文件, 防止 Zip Slip (CWE-22) 漏洞.
"""

import logging
import os
from pathlib import Path
from typing import Union
from zipfile import ZipFile, ZipInfo

logger = logging.getLogger(__name__)


class UnsafeArchiveError(Exception):
    """当归档文件中包含可能逃逸目标目录的成员时抛出.

    包括但不限于: 绝对路径, 包含 `..` 的相对路径穿越,
    解析后落在目标目录之外的路径, 指向目录外部的符号链接等
    """


def safe_extract_zip(zip_file: Union[str, Path, ZipFile], local_path: Union[str, os.PathLike]) -> None:
    """安全解压 zip 归档文件到指定目录, 在写出每个成员之前进行路径检查, 防止 Zip Slip 漏洞.

    :param zip_file: ZIP 文件路径或已打开的 ZipFile 对象
    :param local_path: 解压目标目录
    :raises UnsafeArchiveError: 如果归档文件中包含不安全的成员路径
    """
    base = Path(local_path).resolve()

    # 确保 base 目录存在
    base.mkdir(parents=True, exist_ok=True)

    should_close = False
    if isinstance(zip_file, ZipFile):
        zf = zip_file
    else:
        zf = ZipFile(str(zip_file), "r")
        should_close = True

    try:
        for info in zf.infolist():
            _validate_zip_info(info, base)
        # 所有成员校验通过, 执行解压
        for info in zf.infolist():
            zf.extract(info, path=str(base))
    finally:
        if should_close:
            zf.close()


def _validate_zip_info(info: ZipInfo, base: Path) -> None:
    """校验单个 zip 成员的安全性

    :param info: ZipInfo 对象
    :param base: 解压目录的绝对路径 (已 resolve)
    :raises UnsafeArchiveError: 如果成员路径不安全
    """
    name = info.filename

    # 不允许绝对路径
    if os.path.isabs(name):
        logger.warning("Zip archive contains a member with absolute path: %s, extraction denied", name)
        raise UnsafeArchiveError(f"Zip member '{name}' has an absolute path, which is not allowed")

    # 归一化后校验最终路径是否在 base 目录下
    target_path = (base / name).resolve()
    if not target_path.is_relative_to(base):
        logger.warning(
            "Zip archive contains a path traversal member: %s (resolves to %s), extraction denied", name, target_path
        )
        raise UnsafeArchiveError(
            f"Zip member '{name}' resolves to '{target_path}', which is outside the target directory '{base}'"
        )
