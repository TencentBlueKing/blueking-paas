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
	"os/exec"

	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// pindCmdProvider podman-in-docker command provider
type pindCmdProvider struct {
	execPath string
}

// StartDaemon returns the command to start container daemon
func (p *pindCmdProvider) StartDaemon() *exec.Cmd {
	return utils.Command(p.execPath, "system", "service", "--time", "0")
}

// LoadImage returns the command to load tar to image
func (p *pindCmdProvider) LoadImage(tar string) *exec.Cmd {
	return utils.Command(p.execPath, "load", "-i", tar)
}

// SaveImage returns the command to save image
func (p *pindCmdProvider) SaveImage(image string, destTAR string) *exec.Cmd {
	return utils.Command(p.execPath, "save", "-o", destTAR, "--format", "oci-archive", image)
}

// RunImage returns the command to run image
func (p *pindCmdProvider) RunImage(image string, args ...string) *exec.Cmd {
	runArgs := []string{"run"}
	runArgs = append(runArgs, args...)
	runArgs = append(runArgs, image)
	return exec.Command(p.execPath, runArgs...)
}

// NewPindCmdProvider new pind command provider
func NewPindCmdProvider() (*pindCmdProvider, error) {
	execPath, err := exec.LookPath("podman")
	if err != nil {
		return nil, errors.New("podman command not found")
	}
	return &pindCmdProvider{execPath: execPath}, nil
}
