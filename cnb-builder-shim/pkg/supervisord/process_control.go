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

package supervisord

// ProcessInfo stores information about a process
// https://supervisord.org/api.html#process-control
type ProcessInfo struct {
	Name          string `xmlrpc:"name"`
	Group         string `xmlrpc:"group"`
	Description   string `xmlrpc:"description"`
	Start         int    `xmlrpc:"start"`
	Stop          int    `xmlrpc:"stop"`
	Now           int    `xmlrpc:"now"`
	State         int    `xmlrpc:"state"`
	StateName     string `xmlrpc:"statename"`
	Logfile       string `xmlrpc:"logfile"`
	StdoutLogfile string `xmlrpc:"stdout_logfile"`
	StderrLogfile string `xmlrpc:"stderr_logfile"`
	SpawnErr      string `xmlrpc:"spawnerr"`
	ExitStatus    int    `xmlrpc:"exitstatus"`
	Pid           int    `xmlrpc:"pid"`
}

type ProcessState int

// Process states
// https://supervisord.org/subprocess.html#process-states
const (
	Stopped  ProcessState = 0    // The process has been stopped due to a stop request or has never been started
	Starting ProcessState = 10   // The process is starting due to a start request
	Running  ProcessState = 20   // The process is running
	Backoff  ProcessState = 30   // The process entered the StateStarting state but subsequently exited too quickly to move to the StateRunning state
	Stopping ProcessState = 40   // The process is stopping due to a stop request
	Exited   ProcessState = 100  // The process exited from the StateRunning state (expectedly or unexpectedly)
	Fatal    ProcessState = 200  // The process could not be started successfully
	Unknown  ProcessState = 1000 // The process is in an unknown state (supervisord programming error)
)

func (c *Client) callForProcessInfos(method string, args ...interface{}) ([]ProcessInfo, error) {
	var processInfo []ProcessInfo
	err := c.rpcClient.Call(method, args, &processInfo)
	if err != nil {
		return nil, err
	}

	return processInfo, nil
}

// GetProcessInfo ...
func (c *Client) GetProcessInfo(name string) (*ProcessInfo, error) {
	var processinfo ProcessInfo
	err := c.rpcClient.Call("supervisor.getProcessInfo", name, &processinfo)
	if err != nil {
		return nil, err
	}

	return &processinfo, nil
}

// GetAllProcessInfo ...
func (c *Client) GetAllProcessInfo() ([]ProcessInfo, error) {
	return c.callForProcessInfos("supervisor.getAllProcessInfo")
}

// StartProcess ...
func (c *Client) StartProcess(name string, wait bool) error {
	return c.CallMethodAndVerifyBool("supervisor.startProcess", name, wait)
}

// StartAllProcesses ...
func (c *Client) StartAllProcesses(wait bool) ([]ProcessInfo, error) {
	return c.callForProcessInfos("supervisor.startAllProcesses", wait)
}

// StartProcessGroup ...
func (c *Client) StartProcessGroup(name string, wait bool) ([]ProcessInfo, error) {
	return c.callForProcessInfos("supervisor.startProcessGroup", name, wait)
}

// StopProcess ...
func (c *Client) StopProcess(name string, wait bool) error {
	return c.CallMethodAndVerifyBool("supervisor.stopProcess", name, wait)
}

// StopProcessGroup ...
func (c *Client) StopProcessGroup(name string, wait bool) ([]ProcessInfo, error) {
	return c.callForProcessInfos("supervisor.stopProcessGroup", name, wait)
}

// StopAllProcesses ...
func (c *Client) StopAllProcesses(wait bool) ([]ProcessInfo, error) {
	return c.callForProcessInfos("supervisor.stopAllProcesses", wait)
}

// ReloadConfig ...
func (c *Client) ReloadConfig() ([]string, []string, []string, error) {
	result := make([][][]string, 0)

	err := c.rpcClient.Call("supervisor.reloadConfig", nil, &result)
	if err != nil {
		return nil, nil, nil, err
	}

	return result[0][0], result[0][1], result[0][2], err
}

// Update ...
func (c *Client) Update() error {
	added, changed, removed, err := c.ReloadConfig()
	if err != nil {
		return err
	}

	toStart := append(added, changed...)
	toStop := append(changed, removed...)

	for _, name := range toStop {
		_, err = c.StopProcessGroup(name, true)
		if err != nil {
			return err
		}

		err = c.RemoveProcessGroup(name)
		if err != nil {
			return err
		}
	}

	for _, name := range toStart {
		err = c.AddProcessGroup(name)
		if err != nil {
			return err
		}
	}

	return nil
}

// AddProcessGroup ...
func (c *Client) AddProcessGroup(name string) error {
	return c.CallMethodAndVerifyBool("supervisor.addProcessGroup", name)
}

// RemoveProcessGroup ...
func (c *Client) RemoveProcessGroup(name string) error {
	return c.CallMethodAndVerifyBool("supervisor.removeProcessGroup", name)
}
