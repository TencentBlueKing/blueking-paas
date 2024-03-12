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
	"path"
	"path/filepath"
	"strings"

	"github.com/google/uuid"

	dc "github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devcontainer"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/appdesc"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

// deployStepOpts 表示 Deploy 的步骤选项. 为 true 表示需要执行该步骤
type deployStepOpts struct {
	Rebuild  bool
	Relaunch bool
}

// DeployResult 表示 Deploy 的结果
// TODO 持久化
type DeployResult struct {
	DeployID string
	Status   dc.ReloadStatus
	StepOpts *deployStepOpts
	Log      string
}

// DeployServiceHandler 接口
type DeployServiceHandler interface {
	// Deploy deploys the source file to the application directory.
	Deploy(srcFilePath string) (*DeployResult, error)
	// Result returns the deploy result for a given deploy ID.
	Result(deployID string, withLog bool) (*DeployResult, error)
}

// NewDeployManager returns a new instance of DeployManager.
//
// It initializes the DeployManager struct with default values for the stepOpts field.
//
// Returns a pointer to the newly created DeployManager instance.
func NewDeployManager() *DeployManager {
	return &DeployManager{stepOpts: &deployStepOpts{true, true}}
}

// DeployManager 管理部署
type DeployManager struct {
	stepOpts *deployStepOpts
}

// Deploy deploys the source file to the application directory.
//
// It analyzes the source code and copies it to the application directory.
//
// Parameters:
// - srcFilePath: The path of the source file to be deployed.
//
// Returns:
// - *DeployResult: The deployment result.
// - error: Any error that occurred during the deployment process.
func (m *DeployManager) Deploy(srcFilePath string) (*DeployResult, error) {
	deployID := m.newDeployID()

	// 分析源码并拷贝到应用目录
	if err := m.analyzeAndSyncToAppDir(srcFilePath, dc.DefaultAppDir); err != nil {
		return nil, err
	}

	// 生成 Procfile
	if err := m.generateProcfile(dc.DefaultAppDir); err != nil {
		return nil, err
	}

	// 修改 app 目录的权限
	if err := utils.Chownr(dc.DefaultAppDir, dc.GetCNBUID(), dc.GetCNBGID()); err != nil {
		return nil, err
	}

	return &DeployResult{DeployID: deployID, StepOpts: m.stepOpts, Status: dc.ReloadProcessing}, nil
}

// Result returns the deploy result for a given deploy ID.
//
// Parameters:
// - deployID: The ID of the deploy.
// - withLog: Whether to include the deploy log in the result.
func (m DeployManager) Result(deployID string, withLog bool) (*DeployResult, error) {
	var err error

	storage, err := dc.NewReloadResultStorage()
	if err != nil {
		return nil, err
	}

	result := &DeployResult{DeployID: deployID}

	if result.Status, err = storage.ReadStatus(deployID); err != nil {
		return nil, err
	}

	if !withLog {
		return result, nil
	}

	if result.Log, err = storage.ReadLog(deployID); err != nil {
		return nil, err
	}

	return result, nil
}

func (m DeployManager) newDeployID() string {
	uuidString := uuid.NewString()
	return strings.Replace(uuidString, "-", "", -1)
}

func (m *DeployManager) analyzeAndSyncToAppDir(srcFilePath, appDir string) error {
	tmpDir, err := os.MkdirTemp("", "source-*")
	if err != nil {
		return err
	}
	defer os.RemoveAll(tmpDir)

	// 1. 解压文件到临时目录
	if err = utils.Unzip(srcFilePath, tmpDir); err != nil {
		return err
	}

	fileName := filepath.Base(srcFilePath)
	tmpAppDir := path.Join(tmpDir, strings.Split(fileName, ".")[0])

	// 2. 通过对比新旧文件的变化, 确定哪些步骤需要执行
	m.stepOpts = parseDeployStepOpts(appDir, tmpAppDir)

	// 3. 将 tmpAppDir 中的文件拷贝到 appDir
	if err = m.syncFiles(tmpAppDir, appDir); err != nil {
		return err
	}

	return nil
}

func (m DeployManager) syncFiles(srcDir, appDir string) error {
	// 1. 删除 appDir 下的文件(除了隐藏文件)
	oldFiles, err := filepath.Glob(appDir + "/[^.]*")
	if err != nil {
		return err
	}
	for _, f := range oldFiles {
		if err = os.RemoveAll(f); err != nil {
			return err
		}
	}

	// 2. 将 srcDir 中的文件拷贝到 appDir
	return utils.CopyDir(srcDir, appDir)
}

func (m DeployManager) generateProcfile(appDir string) error {
	if procfile, err := appdesc.TransformToProcfile(path.Join(appDir, "app_desc.yaml")); err != nil {
		return err
	} else {
		if writeErr := os.WriteFile(path.Join(appDir, "Procfile"), []byte(procfile), 0o644); writeErr != nil {
			return writeErr
		}
	}

	return nil
}

// parseDeployStepOpts generates deployStepOpts based on comparing build dependent files.
//
// Parameters:
//
//	oldDir string - the directory where old build dependent files are located
//	newDir string - the directory where new build dependent files are located
func parseDeployStepOpts(oldDir, newDir string) *deployStepOpts {
	buildDependentFiles := []string{"requirements.txt", "Aptfile", "runtime.txt"}
	rebuild := false

	for _, fileName := range buildDependentFiles {
		oldFilePath := path.Join(oldDir, fileName)
		newFilePath := path.Join(newDir, fileName)

		_, newErr := os.Stat(newFilePath)

		// ignore if build dependent file does not exist
		if os.IsNotExist(newErr) {
			continue
		}
		// 根据目前 requirements.txt, Aptfile, runtime.txt 文件特点, 使用 SortedCompareFile 进行文件比较
		// TODO 针对不同的依赖文件, 提供更准确的比较方案
		eq, err := utils.SortedCompareFile(oldFilePath, newFilePath)
		if err != nil || !eq {
			rebuild = true
			break
		}

	}

	return &deployStepOpts{Rebuild: rebuild, Relaunch: true}
}

var _ DeployServiceHandler = (*DeployManager)(nil)

// FakeDeployManger 用于测试
type FakeDeployManger struct{}

// Deploy TODO
func (m *FakeDeployManger) Deploy(srcFilePath string) (*DeployResult, error) {
	return &DeployResult{
		DeployID: uuid.NewString(),
		Status:   dc.ReloadProcessing,
		StepOpts: &deployStepOpts{Relaunch: true, Rebuild: true},
	}, nil
}

// Result TODO
func (m FakeDeployManger) Result(deployID string, withLog bool) (*DeployResult, error) {
	if withLog {
		return &DeployResult{
			DeployID: deployID,
			Status:   dc.ReloadSuccess,
			StepOpts: &deployStepOpts{Relaunch: true, Rebuild: true},
			Log:      "build done...",
		}, nil
	}

	return &DeployResult{
		DeployID: deployID,
		Status:   dc.ReloadSuccess,
		StepOpts: &deployStepOpts{Relaunch: true, Rebuild: true},
	}, nil
}

var _ DeployServiceHandler = (*FakeDeployManger)(nil)
