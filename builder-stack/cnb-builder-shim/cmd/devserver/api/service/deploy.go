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
	"strings"
	"os"
	"fmt"
	"os/exec"
	"bytes"
	"path/filepath"

	"gopkg.in/yaml.v3"
	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

const (
	defaultAppDir = "/app"
	deployDir     = "/cnb/devcontainer/deploy"
)

// Process ...
type Process struct {
	Command string `yaml:"command"`
}

// AppDesc ...
type AppDesc struct {
	SpecVersion string `yaml:"spec_version"`
	Module      struct {
		Processes map[string]Process `yaml:"processes"`
	} `yaml:"module"`
}

// DeployManager ...
type DeployManager struct{}

// Deploy ...
func (m DeployManager) Deploy(filePath string) (string, error) {
	deployID, _ := utils.Md5(filePath)

	if _, err := os.Stat(m.resultFilePath(deployID)); err == nil {
		return deployID, nil
	}

	if err := m.syncToAppDir(filePath, deployID); err != nil {
		return "", errors.Wrap(err, "sync file err")
	}

	// 创建部署记录空文件, 触发 inotifywait 监听事件, 执行 lifecycle-driver
	if _, err := os.Create(m.resultFilePath(deployID)); err != nil {
		return "", errors.Wrap(err, "create release file err")
	}

	return deployID, nil
}

// Result ...
func (m DeployManager) Result(deployID string, withLog bool) (status string, deployLog string, err error) {
	status, deployLog, err = "", "", nil

	if withLog {
		deployLogBytes, logErr := os.ReadFile(m.resultLogFilePath(deployID))
		if logErr != nil {
			err = logErr
			return
		}
		deployLog = string(deployLogBytes)
	}

	code, err := os.ReadFile(m.resultFilePath(deployID))
	if err != nil {
		return
	}

	switch strings.TrimRight(string(code), "\n") {
	case "0":
		status = "Success"
		return
	case "":
		status = "Processing"
		return
	default:
		status = "Failed"
		return
	}

}

func (m DeployManager) syncToAppDir(filePath, md5String string) error {
	tmpDir := "/tmp/" + md5String
	if err := utils.CreateDir(tmpDir); err != nil {
		return err
	}

	if err := unzip(filePath, tmpDir); err != nil {
		return err
	}

	fileName := filepath.Base(filePath)
	fileNameDir := strings.Split(fileName, ".")[0]

	tmpAppPath := tmpDir + "/" + fileNameDir
	if err := m.generateProcfile(tmpAppPath); err != nil {
		return err
	}

	if err := m.syncFiles(tmpAppPath); err != nil {
		return err
	}

	return nil
}

func (m DeployManager) generateProcfile(fileDir string) error {
	yamlFile, err := os.ReadFile(fileDir + "/app_desc.yaml")
	if err != nil {
		return err
	}

	desc := AppDesc{}
	if err = yaml.Unmarshal(yamlFile, &desc); err != nil {
		return err
	}

	lines := []string{}
	for pType, p := range desc.Module.Processes {
		lines = append(lines, fmt.Sprintf("%s: %s", pType, p.Command))
	}

	return os.WriteFile(fileDir+"/Procfile", []byte(strings.Join(lines, "\n")), 0644)

}

func (m DeployManager) syncFiles(srcDir string) error {
	script := m.makeSyncScript(srcDir, defaultAppDir)

	cmd := exec.Command("bash")
	cmd.Stdin = bytes.NewBufferString(script)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return err
	}
	return nil

}

func (m DeployManager) makeSyncScript(srcDir, distDir string) string {
	return fmt.Sprintf(`#! /bin/bash

rm -rf %[2]s/*
mv %[1]s/* %[2]s/
chown -R cnb.cnb %[2]s

rm -rf %[1]s

echo "code sync done"
`, srcDir, distDir)
}

func (m DeployManager) resultFilePath(deployID string) string {
	return deployDir + "/" + deployID
}

func (m DeployManager) resultLogFilePath(deployID string) string {
	return fmt.Sprintf("%s/log/%s.log", deployDir, deployID)
}

func unzip(filePath, distDir string) error {
	cmd := exec.Command("bash", "-c", fmt.Sprintf("unzip -o -q %s -d %s", filePath, distDir))

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return err
	}
	return nil
}
