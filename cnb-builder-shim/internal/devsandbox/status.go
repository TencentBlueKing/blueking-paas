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

package devsandbox

import (
	"bytes"
	"os"
	"strings"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/phase"
)

var statusSubCommand = "status"

// Status returns the status of all processes.
func Status() (map[string]string, error) {
	statusOutput, err := status()
	if err != nil {
		return nil, err
	}
	return parseStatusOutput(statusOutput), nil
}

func status() (string, error) {
	var outBuffer bytes.Buffer

	cmd := phase.MakeLauncherCmd(statusSubCommand)
	cmd.Stdin = os.Stdin
	cmd.Stdout = &outBuffer
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	if err != nil {
		return "", err
	}
	return outBuffer.String(), nil
}

// parses the output from the `supervisorctl status` command.
// The expected format of each line in the output is:
// <process_name> <process_state> <description>
//
// Parameters:
// - output: A string containing the entire output from the `supervisorctl status` command.
//
// Returns:
// - A map with process names as keys and their states as values.
func parseStatusOutput(output string) map[string]string {
	result := make(map[string]string)

	// 按行分割输出
	lines := strings.Split(output, "\n")
	for _, line := range lines {
		// 移除空白符并检查是否为空行
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		// 按空格分割，格式为 "<process_name> <process_state> ..."
		parts := strings.Fields(line)
		if len(parts) < 2 {
			// 如果格式不符合预期，跳过该行
			continue
		}
		// 提取进程名称和状态
		processName := parts[0]
		processState := parts[1]

		result[processName] = processState
	}

	return result
}
