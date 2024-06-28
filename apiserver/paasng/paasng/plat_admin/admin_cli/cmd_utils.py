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

import sys
from typing import Any


class CommandBasicMixin:
    """Provide some basic functionalities for adm cli commands"""

    style: Any
    stdout: Any
    stderr: Any

    def exit_with_error(self, message: str, code: int = 2):
        """Exit execution and print error message"""
        self.stderr.write(self.style.NOTICE(f"Error: {message}"))
        sys.exit(2)

    def print(self, message: str, title: str = "") -> None:
        """A simple wrapper for print function, can be replaced with other implementations

        :param message: The message to be printed
        :param title: Use this title to distinguish different print messages
        """
        if title:
            self.stdout.write(self.style.SUCCESS(f"[{title.upper()}] ") + message)
        else:
            self.stdout.write(message)
