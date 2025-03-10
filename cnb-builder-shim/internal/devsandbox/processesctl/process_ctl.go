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
	"os"
	"path/filepath"
	"strings"
	"text/template"

	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/appdesc"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/supervisord/rpc"
)

var supervisorDir = "/cnb/devsandbox/supervisor"
var rpcPort = "9001"
var rpcAddress = "http://127.0.0.1:9001/RPC2"

var confFilePath = filepath.Join(supervisorDir, "dev.conf")

var confTmpl = `[unix_http_server]
file = {{ .RootDir }}/supervisor.sock

[supervisorctl]
serverurl = unix://{{ .RootDir }}/supervisor.sock

[supervisord]
pidfile = {{ .RootDir }}/supervisord.pid
logfile = {{ .RootDir }}/log/supervisord.log
{{- if .Environment }}
environment = {{ .Environment }}
{{- end }}

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface
{{ range .Processes }}
[program:{{ .ProcType }}]
command = {{ .CommandPath }}
stdout_logfile = {{ .ProcLogFile }}
redirect_stderr = true
{{ end }}
[inet_http_server]
port=127.0.0.1:{{ .Port }}
`

type Process struct {
	ProcType    string
	CommandPath string
}

// ProcessConf is a process config
type ProcessConf struct {
	Process
	ProcLogFile string
}

// SupervisorConf is a supervisor template conf data
type SupervisorConf struct {
	RootDir     string
	Port        string
	Processes   []ProcessConf
	Environment string
}

// returns a new SupervisorConf
func makeSupervisorConf(processes []Process, procEnvs ...appdesc.Env) (*SupervisorConf, error) {
	conf := &SupervisorConf{
		RootDir: supervisorDir,
		Port:    rpcPort,
	}

	if procEnvs != nil {
		if err := validateEnvironment(procEnvs); err != nil {
			return nil, err
		}
		envs := make([]string, len(procEnvs))
		for indx, env := range procEnvs {
			envs[indx] = fmt.Sprintf(`%s="%s"`, env.Name, env.Value)
		}
		conf.Environment = strings.Join(envs, ",")
	}

	for _, p := range processes {
		conf.Processes = append(conf.Processes, ProcessConf{
			Process:     p,
			ProcLogFile: filepath.Join(conf.RootDir, "log", p.ProcType+".log"),
		})
	}
	return conf, nil
}

func refreshConf(conf *SupervisorConf) error {
	tmplFile := "supervisord.conf.tmpl"

	tmpl, err := template.New(tmplFile).Parse(confTmpl)
	if err != nil {
		return err
	}

	file, err := os.Create(confFilePath)
	if err != nil {
		return err
	}
	defer file.Close()

	return tmpl.Execute(file, *conf)
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
	Reload() error
	// StopAllProcesses 停止所有进程
	StopAllProcesses() error
}

// ControllerType 定义控制器类型
type ControllerType string

const (
	RPC ControllerType = "rpc"
)

// NewProcessController 根据类型返回不同的 ProcessCtl 实现
func NewProcessController(controllerType ControllerType) (ProcessCtl, error) {
	switch controllerType {
	case RPC:
		return newRPCProcessController()
	default:
		return nil, errors.New("unsupported controller type")
	}
}

// RPCProcessController ...
type RPCProcessController struct {
	client *rpc.Client
}

// 创建 RPC 类型的 ProcessController
func newRPCProcessController() (*RPCProcessController, error) {
	client, err := rpc.StartServerAndNewClient(rpcAddress, confFilePath)
	if err != nil {
		return nil, err
	}
	return &RPCProcessController{
		client: client,
	}, nil
}

// Status 获取所有进程的状态
func (p *RPCProcessController) Status() ([]rpc.ProcessInfo, error) {
	return p.client.GetAllProcessInfo()
}

// Stop 停止(不是删除)进程
func (p *RPCProcessController) Stop(name string) error {
	return p.client.StopProcess(name, true)
}

// Start 启动进程（只能操作已存在的进程）
func (p *RPCProcessController) Start(name string) error {
	return p.client.StartProcess(name, true)
}

// RefreshConf 重新生成配置文件
func RefreshConf(processes []Process, procEnvs ...appdesc.Env) error {
	conf, err := makeSupervisorConf(processes, procEnvs...)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Join(conf.RootDir, "log"), 0o755); err != nil {
		return err
	}
	if err := refreshConf(conf); err != nil {
		return err
	}
	return nil
}

// Reload 更新和重启进程列表
func (p *RPCProcessController) Reload() error {
	return p.client.Restart()
}

// StopAllProcesses 停止所有进程
func (p *RPCProcessController) StopAllProcesses() error {
	_, err := p.client.StopAllProcesses(true)
	return err
}
