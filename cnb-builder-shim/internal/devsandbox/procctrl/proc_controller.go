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

package procctrl

import (
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/procctrl/procdef"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/procctrl/supervisor"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/appdesc"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/supervisord/rpc"
)

// ProcessCtl 用于进程控制的接口
type ProcessCtl interface {
	// Status 获取所有进程的状态
	Status() ([]rpc.ProcessInfo, error)
	// Start 启动进程（只能操作已存在的进程）
	Start(name string) error
	// Stop 停止(不是删除)进程
	Stop(name string) error
	// Reload 批量更新和重启进程列表
	Reload(processes []procdef.Process, procEnvs ...appdesc.Env) error
	// StopAllProcesses 停止所有进程
	StopAllProcesses() error
}

// NewProcessController ...
func NewProcessController() (ProcessCtl, error) {
	// 暂时只支持一种类型的进程控制，后续可以根据需求扩展
	return supervisor.NewSupervisorRPCProcessController()
}
