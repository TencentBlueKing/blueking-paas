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
	"time"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/appdesc"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/supervisord/rpc"
)

var supervisorDir = "/cnb/devsandbox/supervisor"
var rpcPort = "9001"
var rpcAddress = "http://127.0.0.1:9001/RPC2"

var confFilePath = filepath.Join(supervisorDir, "dev.conf")
var controllerType = SupervisorRPC
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

// RPCProcessController ...
type SupervisorRPCProcessController struct {
	client *rpc.Client
}

// 创建 Supervisor RPC 类型的 ProcessController
func newSupervisorRPCProcessController() (*SupervisorRPCProcessController, error) {
	client, err := rpc.NewClient(rpcAddress)
	if err != nil {
		return nil, err
	}
	return &SupervisorRPCProcessController{
		client: client,
	}, nil
}

// Status 获取所有进程的状态
func (p *SupervisorRPCProcessController) Status() ([]rpc.ProcessInfo, error) {
	return p.client.GetAllProcessInfo()
}

// Stop 停止(不是删除)进程
func (p *SupervisorRPCProcessController) Stop(name string) error {
	return p.client.StopProcess(name, true)
}

// Start 启动进程（只能操作已存在的进程）
func (p *SupervisorRPCProcessController) Start(name string) error {
	return p.client.StartProcess(name, true)
}

// Reload 更新和重启进程列表
func (p *SupervisorRPCProcessController) Reload(processes []Process, procEnvs ...appdesc.Env) error {
	if err := RefreshConf(processes, procEnvs...); err != nil {
		return err
	}
	// 首次运行，没有 supervisor server，直接启动
	server := rpc.NewServer(confFilePath)
	_ = server.Start()
	time.Sleep(1 * time.Second)
	return p.client.Restart()
}

// StopAllProcesses 停止所有进程
func (p *SupervisorRPCProcessController) StopAllProcesses() error {
	_, err := p.client.StopAllProcesses(true)
	return err
}
