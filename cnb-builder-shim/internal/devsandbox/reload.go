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
	"io"
	"os"
	"os/exec"
	"path"

	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/phase"
)

var (
	// ReloadDir used to store reload result
	ReloadDir = "/cnb/devsandbox/reload"
	// ReloadLogDir used to store reload log
	ReloadLogDir = path.Join(ReloadDir, "log")
	// reload sub command of dev-launcher
	reloadSubCommand = "reload"
	// stop sub command of dev-launcher
	stopSubCommand = "stop"
)

// ReloadStatus is the status of a reload operation.
type ReloadStatus string

const (
	// ReloadProcessing represents a reload is in progress.
	ReloadProcessing ReloadStatus = "Processing"
	// ReloadSuccess represents a reload is successful.
	ReloadSuccess ReloadStatus = "Success"
	// ReloadFailed represents a reload is failed.
	ReloadFailed ReloadStatus = "Failed"
	// ReloadUnknown represents a reload is unknown.
	ReloadUnknown ReloadStatus = "Unknown"
)

// NewHotReloadManager creates a new instance of HotReloadManager.
//
// It initializes a ReloadResultStorage and returns a pointer to a HotReloadManager and an error.
func NewHotReloadManager() (*HotReloadManager, error) {
	storage, err := NewReloadResultStorage()
	if err != nil {
		return nil, err
	}
	return &HotReloadManager{storage}, nil
}

// HotReloadManager ...
type HotReloadManager struct {
	ReloadResultStorage
}

// Rebuild ...
func (m HotReloadManager) Rebuild(reloadID string) error {
	// 重新构建前，将所有进程停止，主要解决两个问题
	// 1. 构建完后，supervisor 重启进程会失败，导致只 kill 主进程而子进程变成僵尸进程
	// 2. 构建时，supervisor 会因 terminated by SIGSEGV 发生预期之外进程退出，
	// 然后本身的托管能力又会拉起进程，导致 /app/v3logs 目录权限在 cnb or root
	// 间横跳，从而使构建时遇到 v3logs 文件夹权限错误而构建失败
	cmd := phase.MakeLauncherCmd(stopSubCommand)
	err := m.runCmd(reloadID, cmd)
	if err != nil {
		return err
	}
	cmd = phase.MakeBuilderCmd()
	return m.runCmd(reloadID, cmd)
}

// Relaunch ...
func (m HotReloadManager) Relaunch(reloadID string) error {
	cmd := phase.MakeLauncherCmd(reloadSubCommand)
	return m.runCmd(reloadID, cmd)
}

func (m HotReloadManager) runCmd(reloadID string, cmd *exec.Cmd) error {
	w, err := m.ResultLogWriter(reloadID)
	if err != nil {
		return err
	}
	defer w.Close()

	cmd.Stdin = os.Stdin
	multiWriter := io.MultiWriter(os.Stdout, w)
	cmd.Stdout = multiWriter
	cmd.Stderr = multiWriter

	return cmd.Run()
}

// ReloadResultStorage is the interface that stores the result of app reload.
type ReloadResultStorage interface {
	// ReadStatus returns the reload status for the given reload ID.
	ReadStatus(reloadID string) (ReloadStatus, error)
	// WriteStatus writes the status of a reload operation.
	WriteStatus(reloadID string, status ReloadStatus) error
	// ReadLog is a function that reads a log file based on the given reloadID.
	ReadLog(reloadID string) (string, error)
	// ResultLogWriter is a function that takes a reloadID as a parameter and returns a writer and an error.
	ResultLogWriter(reloadID string) (io.WriteCloser, error)
}

// NewReloadResultStorage makes an instance of ReloadResultStorage.
func NewReloadResultStorage() (ReloadResultStorage, error) {
	// TODO: support other storage
	s := ReloadResultFile{rootDir: ReloadDir, rootLogDir: ReloadLogDir}
	if err := os.MkdirAll(s.rootLogDir, 0o755); err != nil {
		return nil, err
	}
	return s, nil
}

// ReloadResultFile implements ReloadResultStorage with local file system
type ReloadResultFile struct {
	rootDir    string
	rootLogDir string
}

// ReadStatus returns the reload status for the given reload ID.
func (f ReloadResultFile) ReadStatus(reloadID string) (ReloadStatus, error) {
	status, err := os.ReadFile(path.Join(f.rootDir, reloadID))
	if err != nil {
		return ReloadUnknown, errors.Wrap(err, "failed to read status")
	}
	return ReloadStatus(status), nil
}

// WriteStatus writes the status of a reload operation.
func (f ReloadResultFile) WriteStatus(reloadID string, status ReloadStatus) error {
	file, err := os.Create(path.Join(f.rootDir, reloadID))
	if err != nil {
		return errors.Wrap(err, "failed to write status")
	}
	defer file.Close()

	_, err = file.WriteString(string(status))
	return err
}

// ReadLog is a function that reads a log file based on the given reloadID.
func (f ReloadResultFile) ReadLog(reloadID string) (string, error) {
	content, err := os.ReadFile(path.Join(f.rootLogDir, reloadID))
	if err != nil {
		return "", errors.Wrap(err, "failed to read log")
	}
	return string(content), nil
}

// ResultLogWriter is a function that takes a reloadID as a parameter and returns a io.WriteCloser and an error.
// shell command will use this writer to write log
func (f ReloadResultFile) ResultLogWriter(reloadID string) (io.WriteCloser, error) {
	file, err := os.OpenFile(path.Join(f.rootLogDir, reloadID), os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0o644)
	if err != nil {
		return nil, errors.Wrap(err, "failed to open log file")
	}
	return file, nil
}

var _ ReloadResultStorage = (*ReloadResultFile)(nil)
