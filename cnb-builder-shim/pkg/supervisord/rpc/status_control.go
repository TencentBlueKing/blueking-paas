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

package rpc

type (
	// StateCode is a numeric representation of Supervisord's internal state.
	StateCode int

	// StateName is a textual representation of Supervisord's internal state.
	StateName string

	// State represents the current state of the Supervisor.
	State struct {
		Code StateCode `xmlrpc:"statecode"`
		Name StateName `xmlrpc:"statename"`
	}
)

const (
	// StateCodeFatal means supervisor has experienced a serious error.
	StateCodeFatal StateCode = 2
	// StateCodeRunning means supervisor is working normally.
	StateCodeRunning StateCode = 1
	// StateCodeRestarting means supervisor is in the process of restarting.
	StateCodeRestarting StateCode = 0
	// StateCodeShutdown means supervisor is in the process of shutting down.
	StateCodeShutdown StateCode = -1

	// StateNameFatal means supervisor has experienced a serious error.
	StateNameFatal StateName = "FATAL"
	// StateNameRunning means supervisor is working normally.
	StateNameRunning StateName = "RUNNING"
	// StateNameRestarting means supervisor is in the process of restarting.
	StateNameRestarting StateName = "RESTARTING"
	// StateNameShutdown means supervisor is in the process of shutting down.
	StateNameShutdown StateName = "SHUTDOWN"
)

// GetState 获取 Supervisor Server
func (c *Client) GetState() (State, error) {
	var state State
	err := c.rpcClient.Call("supervisor.getState", nil, &state)

	return state, err
}

// Restart 重启 Supervisor Server
func (c *Client) Restart() error {
	var res bool
	err := c.rpcClient.Call("supervisor.restart", nil, &res)
	return err
}
