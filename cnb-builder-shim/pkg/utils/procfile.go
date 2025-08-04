/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package utils

import (
	"fmt"
	"strings"
)

// GenBashCommandWithTokens 生成使用 command + args 的 bash 命令
// Example:
//
//	  Given command = ["python"], args = ["-m", "http.server", "${PORT:-9999}"]
//	  The returned bash script will be:
//
//		  'bash -c \'"$(eval echo \\"$0\\")" "$(eval echo \\"${1}\\")" "$(eval echo \\"${2}\\")" \
//		         "$(eval echo \\"${3}\\")"\' python -m http.server \'${PORT:-9999}\''
//
// After token evaluation, the process will run as a Procfile like: 'python -m http.server ${PORT:-9999}'
//
// ref:
//   - https://github.com/buildpacks/lifecycle/blob/435d226f1ed54b0bec806716ba79e14a2a093736/launch/bash.go#L55
//   - https://github.com/TencentBlueKing/blueking-paas/blob/95b99c5a1a41d31efa3b2270968bfc846102cfcb/apiserver/paasng/paasng/utils/procfile.py#L22
func GenBashCommandWithTokens(command []string, args []string) string {
	// 将 command 和 args 都认为 bash 命令的参数
	tokens := append(command, args...)
	tokenSize := len(tokens)

	// 使用 eval echo 展开每个位置参数（$0, $1, $2...），环境变量亦会生效
	script := `"$(eval echo \"$0\")"`
	for i := 1; i < tokenSize; i++ {
		script += fmt.Sprintf(` "$(eval echo \"${%d}\")"`, i)
	}

	// command + args 作为参数，前后添加单引号
	var sb strings.Builder
	for _, token := range tokens {
		sb.WriteString(" ")
		sb.WriteString(shQuote(token))
	}

	// 拼接结果：bash -c '核心脚本' + 引用后的参数
	return "bash -c " + shQuote(script) + sb.String()
}

// shQuote 将字符串进行单引号转义，用于安全嵌入 Bash 命令
func shQuote(s string) string {
	if s == "" {
		return "''"
	}
	return "'" + strings.ReplaceAll(s, "'", "'\\''") + "'"
}
