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
package filediffer

import (
	"bytes"
	"io"
	"os"
	"os/exec"
	"path"
	"strings"

	"github.com/pkg/errors"
)

// FileDiffer 文件变更对比器
type FileDiffer struct {
	srcPath     string
	withContent bool
}

// New ...
func New(opts ...Option) *FileDiffer {
	differ := &FileDiffer{}
	for _, opt := range opts {
		opt(differ)
	}
	return differ
}

// Prepare 准备步骤
func (d *FileDiffer) Prepare(srcPath string) error {
	d.srcPath = srcPath

	_, err := os.Stat(path.Join(d.srcPath, ".git"))
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
			if _, err = d.runGitCommand(cmd...); err != nil {
				return err
			}
		}
		return nil
	}

	// 其他错误，直接返回
	return err
}

// Diff 对比输出文件变更信息
func (d *FileDiffer) Diff() ([]File, error) {
	if _, err := d.runGitCommand("add", "."); err != nil {
		return nil, err
	}
	output, err := d.runGitCommand("diff", "--cached", "--name-status")
	if err != nil {
		return nil, err
	}

	lines := strings.Split(output, "\n")
	files := []File{}
	for _, line := range lines {
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) != 2 {
			return nil, errors.Errorf("invalid line: %s", line)
		}
		var action FileAction
		switch fields[0] {
		case "A":
			action = FileActionAdded
		case "M":
			action = FileActionModified
		case "D":
			action = FileActionDeleted
		default:
			return nil, errors.Errorf("unknown action: %s", fields[0])
		}
		// 强制忽略部分变更文件
		if d.mustIgnoreFile(fields[1]) {
			continue
		}

		var content string
		// 如果是删除操作，不加载文件
		if d.withContent && action != FileActionDeleted {
			if content, err = d.loadFileContent(fields[1]); err != nil {
				return nil, err
			}
		}
		files = append(files, File{Action: action, Path: fields[1], Content: content})
	}
	return files, nil
}

// 执行 Git 命令
func (d *FileDiffer) runGitCommand(args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	cmd.Dir = d.srcPath

	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out
	if err := cmd.Run(); err != nil {
		return "", errors.Errorf("git command failed: %s, output: %s", err, out.String())
	}

	return out.String(), nil
}

// 加载指定文件内容
func (d *FileDiffer) loadFileContent(filepath string) (string, error) {
	file, err := os.Open(path.Join(d.srcPath, filepath))
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

// 判断变更的文件是否需要被忽略
func (d *FileDiffer) mustIgnoreFile(filepath string) bool {
	for _, prefix := range forceIgnoreFilePathPrefixes {
		if strings.HasPrefix(filepath, prefix) {
			return true
		}
	}
	return false
}

// Option Differ 选项
type Option func(*FileDiffer)

// WithContent Diff 时是否加载文件内容
func WithContent() Option {
	return func(d *FileDiffer) {
		d.withContent = true
	}
}
