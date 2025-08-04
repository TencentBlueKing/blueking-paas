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

package executor

import (
	"fmt"
	"os/exec"

	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/config"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// dindCmdProvider docker-in-docker command provider
type dindCmdProvider struct {
	execPath string
}

// StartDaemon returns the command to start container daemon
func (d *dindCmdProvider) StartDaemon() *exec.Cmd {
	execPath, _ := exec.LookPath("dockerd")
	return utils.Command(execPath)
}

// LoadImage returns the command to load tar to image
func (d *dindCmdProvider) LoadImage(tar string) *exec.Cmd {
	return utils.Command(d.execPath, "-H", fmt.Sprintf("unix://%s", config.G.DaemonSockFile), "load", "-i", tar)
}

// SaveImage returns the command to save image
func (d *dindCmdProvider) SaveImage(image string, destTAR string) *exec.Cmd {
	return utils.Command(
		d.execPath,
		"-H",
		fmt.Sprintf("unix://%s", config.G.DaemonSockFile),
		"save",
		"-o",
		destTAR,
		image,
	)
}

// RunImage returns the command run image
func (d *dindCmdProvider) RunImage(image string, args ...string) *exec.Cmd {
	runArgs := []string{"-H", fmt.Sprintf("unix://%s", config.G.DaemonSockFile), "run"}
	runArgs = append(runArgs, args...)
	runArgs = append(runArgs, image)
	return exec.Command(d.execPath, runArgs...)
}

// NewDindCmdProvider new dind command provider
func NewDindCmdProvider() (*dindCmdProvider, error) {
	execPath, err := exec.LookPath("docker")
	if err != nil {
		return nil, errors.New("docker command not found")
	}
	return &dindCmdProvider{execPath: execPath}, nil
}
