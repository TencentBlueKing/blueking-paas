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

package processctl

import (
	"path/filepath"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/supervisord"
)

var supervisorDir = "/cnb/devsandbox/supervisor"
var RPCAddress = "http://127.0.0.1:9001/RPC2"

var confFilePath = filepath.Join(supervisorDir, "dev.conf")

// ProcessController ...
type ProcessController struct {
	client *supervisord.Client
}

// New ...
func New() (*ProcessController, error) {
	client, err := supervisord.NewClient(supervisord.ClientConfig{
		RPCAddress: RPCAddress,
		ConfigPath: confFilePath,
	})
	if err != nil {
		return nil, err
	}
	return &ProcessController{
		client: client,
	}, nil
}

// Status ...
func (p *ProcessController) Status() ([]supervisord.ProcessInfo, error) {
	return p.client.GetAllProcessInfo()
}

// Stop ...
func (p *ProcessController) Stop(name string) error {
	return p.client.StopProcess(name, true)
}

// Start ...
func (p *ProcessController) Start(name string) error {
	return p.client.StartProcess(name, true)
}
