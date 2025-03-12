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

package processesctl

import (
	"fmt"
	"github.com/pkg/errors"
	"strings"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/appdesc"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/supervisord/rpc"
)

type Process struct {
	ProcType    string
	CommandPath string
}

// ProcessConf is a process config
type ProcessConf struct {
	Process
	ProcLogFile string
}

// validateEnvironment validates the environment variables for supervisor conf.
//
// see detail environment conf in http://supervisord.org/configuration.html
// char " and % in environment value will cause supervisord to fail
func validateEnvironment(procEnvs []appdesc.Env) error {
	invalidChars := `"%`
	invalidEnvNames := []string{}
	for _, env := range procEnvs {
		if strings.ContainsAny(env.Value, invalidChars) {
			invalidEnvNames = append(invalidEnvNames, env.Name)
		}
	}
	if len(invalidEnvNames) == 0 {
		return nil
	}

	return fmt.Errorf(
		"environment variables: %s has invalid characters (%s)",
		strings.Join(invalidEnvNames, ", "),
		invalidChars,
	)
}

// ProcessCtl 用于进程控制的接口
type ProcessCtl interface {
	// Status 获取所有进程的状态
	Status() ([]rpc.ProcessInfo, error)
	// Start 启动进程（只能操作已存在的进程）
	Start(name string) error
	// Stop 停止(不是删除)进程
	Stop(name string) error
	// Reload 更新和重启进程列表
	Reload(processes []Process, procEnvs ...appdesc.Env) error
	// StopAllProcesses 停止所有进程
	StopAllProcesses() error
}

// ControllerType 定义控制器类型
type ControllerType string

const (
	SupervisorRPC ControllerType = "SUPERVISOR_RPC"
)

// NewProcessController 根据类型返回不同的 ProcessCtl 实现
func NewProcessController() (ProcessCtl, error) {
	switch controllerType {
	case SupervisorRPC:
		return newSupervisorRPCProcessController()
	default:
		return nil, errors.New("unknown controller type")
	}
}
