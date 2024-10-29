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
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

func GetAppLogs(logPath string, lines int) (map[string][]string, error) {
	logs := make(map[string][]string)
	logFiles, err := getLatestLogFiles(logPath)
	if err != nil {
		return nil, err
	}
	for logType, files := range logFiles {
		for _, file := range files {
			lastXLines, err := getLastLines(logPath, file.Name(), lines)
			if err != nil {
				continue
			}
			logs[logType] = append(lastXLines, logs[logType]...)
			if len(lastXLines) >= lines {
				break
			}
		}
	}
	return logs, nil
}

// getLatestLogFiles 按日志类型分类，并且获取最新的日志文件列表
// 日志文件名称需要符合格式：{{process_type}}-{{random_str}}-{{log_type}}.log
func getLatestLogFiles(logDir string) (map[string][]os.FileInfo, error) {
	logFiles := make(map[string][]os.FileInfo)
	err := filepath.Walk(logDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		// 过滤非日志文件, 并且根据文件名称将日志进行分类
		if !info.IsDir() && strings.HasSuffix(strings.ToLower(info.Name()), ".log") {
			logName := strings.TrimSuffix(strings.ToLower(info.Name()), filepath.Ext(info.Name()))
			lastDashIndex := strings.LastIndex(logName, "-")
			if lastDashIndex == -1 {
				return fmt.Errorf("invalid log file name: %s", info.Name())
			}
			logType := logName[lastDashIndex+1:]
			logFiles[logType] = append(logFiles[logType], info)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	// 按日志类型进行时间排序
	for _, files := range logFiles {
		sort.Slice(files, func(i, j int) bool {
			return files[i].ModTime().After(files[j].ModTime())
		})
	}
	return logFiles, nil
}

// getLastLines returns the last lines of the log file
func getLastLines(logPath string, fileName string, lines int) ([]string, error) {
	filePath := filepath.Join(logPath, fileName)
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	var logs []string
	scanner := bufio.NewScanner(file)
	// 全量读取日志文件,日志文件都有进行分片,对于内存压力应该还好
	for scanner.Scan() {
		logs = append(logs, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	if len(logs) > lines {
		logs = logs[len(logs)-lines:]
	}
	return logs, nil
}
