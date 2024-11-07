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

package launch

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"text/template"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/appdesc"
)

var supervisorDir = "/cnb/devsandbox/supervisor"

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
{{ end -}}
`

var reloadScript = fmt.Sprintf(`#!/bin/bash

socket_file="%[1]s/supervisor.sock"
# 检查 supervisor 的 socket 文件是否存在
if [ -S "$socket_file" ]; then
  echo "supervisord is already running. update and restart processes..."
  supervisorctl -c %[2]s reload
else
  echo "supervisord is not running. start supervisord..."
  supervisord -c %[2]s
fi
`, supervisorDir, confFilePath)

var statusScript = fmt.Sprintf(`#!/bin/bash

socket_file="%[1]s/supervisor.sock"
# 检查 supervisor 的 socket 文件是否存在
if [ -S "$socket_file" ]; then
  supervisorctl -c %[2]s status
fi
`, supervisorDir, confFilePath)

var stopScript = fmt.Sprintf(`#!/bin/bash

socket_file="%[1]s/supervisor.sock"
# 检查 supervisor 的 socket 文件是否存在
if [ -S "$socket_file" ]; then
  echo "stop all processes..."
  supervisorctl -c %[2]s stop all
fi
`, supervisorDir, confFilePath)

// ProcessConf is a process config
type ProcessConf struct {
	Process
	ProcLogFile string
}

// SupervisorConf is a supervisor template conf data
type SupervisorConf struct {
	RootDir     string
	Processes   []ProcessConf
	Environment string
}

// MakeSupervisorConf returns a new SupervisorConf
func MakeSupervisorConf(processes []Process, procEnvs ...appdesc.Env) (*SupervisorConf, error) {
	conf := &SupervisorConf{
		RootDir: supervisorDir,
	}

	if procEnvs != nil {
		if err := validateEnvironment(procEnvs); err != nil {
			return nil, err
		}
		envs := make([]string, len(procEnvs))
		for indx, env := range procEnvs {
			envs[indx] = fmt.Sprintf(`%s="%s"`, env.Key, env.Value)
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

// NewSupervisorCtl returns a new SupervisorCtl
func NewSupervisorCtl() *SupervisorCtl {
	return &SupervisorCtl{
		RootDir: supervisorDir,
	}
}

// SupervisorCtl is a supervisorctl wrapper with supervisor binary
type SupervisorCtl struct {
	RootDir string
}

// Reload start or update/restart the processes
// TODO: 现在 reload 还是会导致子进程堆积僵尸进程
func (ctl *SupervisorCtl) Reload(conf *SupervisorConf) error {
	if err := os.MkdirAll(filepath.Join(ctl.RootDir, "log"), 0o755); err != nil {
		return err
	}
	if err := ctl.refreshConf(conf); err != nil {
		return err
	}
	return ctl.reload()
}

func (ctl *SupervisorCtl) refreshConf(conf *SupervisorConf) error {
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

func (ctl *SupervisorCtl) reload() error {
	cmd := exec.Command("bash")

	cmd.Env = os.Environ()
	cmd.Stdin = bytes.NewBufferString(reloadScript)
	cmd.Stderr = os.Stderr
	cmd.Stdout = os.Stdout

	return cmd.Run()
}

// Status get the status of all processes by running 'supervisorctl status'.
func (ctl *SupervisorCtl) Status() error {
	cmd := exec.Command("bash")

	cmd.Env = os.Environ()
	cmd.Stdin = bytes.NewBufferString(statusScript)
	cmd.Stderr = os.Stderr
	cmd.Stdout = os.Stdout

	return cmd.Run()
}

// stop all processes by running 'supervisorctl stop all'.
func (ctl *SupervisorCtl) Stop() error {
	cmd := exec.Command("bash")

	cmd.Env = os.Environ()
	cmd.Stdin = bytes.NewBufferString(stopScript)
	cmd.Stderr = os.Stderr
	cmd.Stdout = os.Stdout

	return cmd.Run()
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
			invalidEnvNames = append(invalidEnvNames, env.Key)
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
