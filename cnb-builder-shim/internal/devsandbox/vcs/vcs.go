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
package vcs

import (
	"bytes"
	"io"
	"os"
	"os/exec"
	"path"
	"strings"
	"unicode"

	"github.com/pkg/errors"
)

// VersionController 版本控制器（基于 Git）
type VersionController struct {
	srcPath     string
	withContent bool
}

// New ...
func New(srcPath string, opts ...Option) *VersionController {
	v := &VersionController{
		srcPath: srcPath,
	}
	for _, opt := range opts {
		opt(v)
	}
	return v
}

// Prepare 准备步骤
func (v *VersionController) Prepare() error {
	_, err := os.Stat(path.Join(v.srcPath, ".git"))
	// 如果对应目录下存在 .git 目录，跳过
	if err == nil {
		return nil
	}

	// 没有 .git 目录（使用子目录部署的情况），执行若干命令以初始化
	if os.IsNotExist(err) {
		commands := [][]string{
			{"init"},
			{"add", "."},
			{"config", "user.name", "bkpaas"},
			{"config", "user.email", "bkpaas@example.com"},
			{"commit", "-m", "init"},
		}
		for _, cmd := range commands {
			if _, err = v.runGitCommand(cmd...); err != nil {
				return err
			}
		}
		return nil
	}

	// 其他错误，直接返回
	return err
}

// Diff 对比输出文件变更信息
func (v *VersionController) Diff() (Files, error) {
	if err := v.Prepare(); err != nil {
		return nil, err
	}
	// 将所有文件添加到暂存区
	if _, err := v.runGitCommand("add", "."); err != nil {
		return nil, err
	}
	// 设置不要转义特殊字符
	if _, err := v.runGitCommand("config", "core.quotepath", "false"); err != nil {
		return nil, err
	}
	// 执行 diff 命令输出变更文件目录
	output, err := v.runGitCommand("diff", "--cached", "--name-status", "--no-renames")
	if err != nil {
		return nil, err
	}

	lines := strings.Split(output, "\n")
	files := Files{}
	for _, line := range lines {
		action, filePath, pErr := v.parseDiffLine(line)
		if pErr != nil {
			continue
		}
		// 强制忽略部分变更文件
		if v.shouldIgnoreFile(filePath) {
			continue
		}
		var content string
		// 只有指定要加载 & 不是删除操作时，才会加载文件内容
		if v.withContent && action != FileActionDeleted {
			if content, err = v.loadFileContent(filePath); err != nil {
				return nil, err
			}
		}
		files = append(files, File{Action: action, Path: filePath, Content: content})
	}
	return files, nil
}

// Commit 提交变更
func (v *VersionController) Commit(message string) error {
	if err := v.Prepare(); err != nil {
		return err
	}

	commands := [][]string{
		{"add", "."},
		{"config", "user.name", "bkpaas"},
		{"config", "user.email", "bkpaas@example.com"},
		{"commit", "-m", message},
	}
	for _, cmd := range commands {
		if _, err := v.runGitCommand(cmd...); err != nil {
			return err
		}
	}
	return nil
}

// 执行 Git 命令
func (v *VersionController) runGitCommand(args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	cmd.Dir = v.srcPath

	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out
	if err := cmd.Run(); err != nil {
		return "", errors.Errorf("git command failed: %s, output: %s", err, out.String())
	}

	return out.String(), nil
}

// 加载指定文件内容
func (v *VersionController) loadFileContent(filePath string) (string, error) {
	file, err := os.Open(path.Join(v.srcPath, filePath))
	if err != nil {
		return "", err
	}
	defer file.Close()

	content, err := io.ReadAll(file)
	if err != nil {
		return "", err
	}
	return string(content), nil
}

// 解析 git diff 输出的文件变更信息
func (v *VersionController) parseDiffLine(line string) (FileAction, string, error) {
	// diff 输出格式形如：
	// A       backend/example.go
	// M       webfe/example.js
	// D       api/example.py
	index := strings.IndexFunc(line, unicode.IsSpace)
	if index == -1 {
		return "", "", errors.Errorf("invalid diff line: `%s`", line)
	}

	rawAction, filePath := line[:index], strings.TrimSpace(line[index+1:])
	switch rawAction {
	case "A":
		return FileActionAdded, filePath, nil
	case "M":
		return FileActionModified, filePath, nil
	case "D":
		return FileActionDeleted, filePath, nil
	default:
		return "", "", errors.Errorf("unknown action: %s", rawAction)
	}
}

// 判断变更的文件是否需要被忽略
func (v *VersionController) shouldIgnoreFile(filePath string) bool {
	for _, prefix := range forceIgnoreFilePathPrefixes {
		if strings.HasPrefix(filePath, prefix) {
			return true
		}
	}
	return false
}

// Option VersionController 选项
type Option func(*VersionController)

// WithContent Diff 时加载文件内容
func WithContent() Option {
	return func(v *VersionController) {
		v.withContent = true
	}
}
