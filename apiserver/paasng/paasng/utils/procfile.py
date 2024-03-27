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
import shlex
from typing import List


def generate_bash_command_with_tokens(command: List[str], args: List[str]) -> str:
    """returns a bash script that execute command + args with token trick

    Example:
        Given command = ["python"], args = ["-m", "http.server", "${PORT:-9999}"]
        The returned bash script will be:
          'bash -c \'"$(eval echo \\"$0\\")" "$(eval echo \\"${1}\\")" "$(eval echo \\"${2}\\")" "$(eval echo \\"${3}\\")"\' python -m http.server \'${PORT:-9999}\''

        After token evaluation, the process will run as a Procfile like: 'python -m http.server ${PORT:-9999}'

    ref: https://github.com/buildpacks/lifecycle/blob/435d226f1ed54b0bec806716ba79e14a2a093736/launch/bash.go#L55

    Q: Why not use `shlex.join`?
    A: `shlex.join` will quote all unsafe string, such as `$`, `"`, `'` and so on.
    For example, `shlex.join(["python", "-m", "http.server","${PORT:-9999}"])` will return:
      'python -m http.server \'${PORT:-9999}\''
    But we want:
      'python -m http.server ${PORT:-9999}'
    """
    token_size = len(command) + len(args)
    script = r'"$(eval echo \"$0\")"'
    for i in range(1, token_size):
        script += rf' "$(eval echo \"${{{i}}}\")"'
    script_args = ""
    for s in command + args:
        script_args += f" {shlex.quote(s)}"
    return f"bash -c '{script}' {script_args.lstrip()}"
