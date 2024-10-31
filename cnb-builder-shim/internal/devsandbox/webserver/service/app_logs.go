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

package service

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/docker/docker/pkg/tailfile"
)

// DefaultAppLogDir 应用日志默认目录
var DefaultAppLogDir = "/cnb/devsandbox/supervisor/log"

// GetAppLogs 获取应用日志
// Parameters:
//   - logPath: 日志路径
//   - lines: 需要的日志行数
//
// Returns:
//   - map[string][]string: key 为日志类型, value 为日志内容
func GetAppLogs(logDir string, lines int) (map[string][]string, error) {
	// 检查文件是否存在
	if _, err := os.Stat(logDir); os.IsNotExist(err) {
		// 文件不存在，返回 nil, nil
		return nil, nil
	}
	logs := make(map[string][]string)
	logFiles, err := getLogFiles(logDir)
	if err != nil {
		return nil, err
	}
	for logType, file := range logFiles {
		logPath := filepath.Join(logDir, file.Name())
		logLines, err := tailFile(logPath, lines)
		if err != nil {
			return nil, err
		}
		logs[logType] = logLines
	}
	return logs, nil
}

// 按日志类型分类日志文件
func getLogFiles(logDir string) (map[string]os.FileInfo, error) {
	logFiles := make(map[string]os.FileInfo)
	err := filepath.Walk(logDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		// 获取日志类型
		logType := getLogType(info)
		if logType != "" {
			logFiles[logType] = info
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	return logFiles, nil
}

// 通过文件名称获取日志类型, 需要符合格式：{{type}}.log
func getLogType(info os.FileInfo) string {
	if !info.IsDir() && strings.HasSuffix(strings.ToLower(info.Name()), ".log") {
		logType := strings.TrimSuffix(strings.ToLower(info.Name()), filepath.Ext(info.Name()))
		return logType
	}
	return ""
}

// 获取文件最新部分的内容
func tailFile(filePath string, lines int) (logs []string, err error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	tailBytes, err := tailfile.TailFile(file, lines)
	if err != nil {
		return nil, err
	}
	tailStr := make([]string, len(tailBytes))
	for index, b := range tailBytes {
		tailStr[index] = string(b)
	}

	logs = append(logs, tailStr...)
	return logs, nil
}
