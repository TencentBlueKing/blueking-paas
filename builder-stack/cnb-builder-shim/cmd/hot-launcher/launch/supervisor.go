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
	"os"
	"text/template"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

var supervisorDir = utils.EnvOrDefault("SUPERVISOR_DIR", "/cnb/devcontainer/supervisor")

// Process is a process to launch
type Process struct {
	ProcType string
	Command  string
}

// ProcessConf is a process config
type ProcessConf struct {
	Process
	ProcLogFile string
}

// SupervisorConf is a supervisor template conf data
type SupervisorConf struct {
	RootDir   string
	Processes []ProcessConf
}

func MakeSupervisorConf(processes []Process) *SupervisorConf {
	conf := &SupervisorConf{
		RootDir: supervisorDir,
	}

	for _, p := range processes {
		conf.Processes = append(conf.Processes, ProcessConf{
			Process:     p,
			ProcLogFile: conf.RootDir + "/log/" + p.ProcType + ".log",
		})
	}
	return conf
}

// NewSupervisorCtl returns a new SupervisorCtl
func NewSupervisorCtl() *SupervisorCtl {
	return &SupervisorCtl{
		RootDir: supervisorDir,
	}
}

type SupervisorCtl struct {
	RootDir string
}

// Reload start or update/restart the processes
func (ctl *SupervisorCtl) Reload(conf *SupervisorConf) error {
	if err := createDir(ctl.RootDir + "/log"); err != nil {
		return err
	}

	if err := ctl.refreshConf(conf); err != nil {
		return err
	}
	return ctl.reload()
}

func (ctl *SupervisorCtl) refreshConf(conf *SupervisorConf) error {
	tmplFile := "supervisord.conf.tmpl"

	tmpl, err := template.New(tmplFile).ParseFiles("templates/" + tmplFile)
	if err != nil {
		return err
	}

	file, err := os.Create(ctl.RootDir + "/dev.conf")
	if err != nil {
		return err
	}
	defer file.Close()

	return tmpl.Execute(file, *conf)
}

func (ctl *SupervisorCtl) reload() error {
	return nil
}
