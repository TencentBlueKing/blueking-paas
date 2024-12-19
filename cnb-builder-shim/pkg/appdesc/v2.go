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

package appdesc

import "github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/config"

// ProcessV2 ...
type ProcessV2 struct {
	Command string `yaml:"command"`
}

// EnvV2 ...
type EnvV2 struct {
	Key   string `yaml:"key"`
	Value string `yaml:"value"`
}

// ModuleV2 ...
type ModuleV2 struct {
	Processes map[string]ProcessV2 `yaml:"processes"`
	Scripts   struct {
		PreReleaseHook string `yaml:"pre_release_hook"`
	} `yaml:"scripts"`
	ProcEnvs []EnvV2 `yaml:"env_variables"`
}

// AppDescV2 ...
type AppDescV2 struct {
	SpecVersion string               `yaml:"spec_version"`
	Module      *ModuleV2            `yaml:"module"`
	Modules     map[string]*ModuleV2 `yaml:"modules"`
}

// GetModule returns the ModuleV2 object.
// If Module is not nil, it is returned directly.
// If the moduleName is empty, nil is returned.
// Otherwise, it looks up and returns the module specified by moduleName from the Modules map.
func (d *AppDescV2) GetModule() *ModuleV2 {
	moduleName := config.G.ModuleName
	if d.Module != nil {
		return d.Module
	}
	if moduleName == "" {
		return nil
	}
	return d.Modules[moduleName]
}

// GetProcesses ...
func (d *AppDescV2) GetProcesses() []Process {
	module := d.GetModule()
	if module == nil {
		return nil
	}
	processes := make([]Process, len(module.Processes))
	index := 0
	for pType, p := range module.Processes {
		processes[index] = Process{
			Name:        pType,
			ProcCommand: p.Command,
		}
		index++
	}
	return processes
}

// GetPreReleaseHook ...
func (d *AppDescV2) GetPreReleaseHook() string {
	module := d.GetModule()
	if module == nil {
		return ""
	}
	return module.Scripts.PreReleaseHook
}

// GetEnvs ...
func (d *AppDescV2) GetEnvs() []Env {
	module := d.GetModule()
	if module == nil {
		return nil
	}
	envs := make([]Env, len(module.ProcEnvs))
	for index, env := range module.ProcEnvs {
		envs[index] = Env{
			Name:  env.Key,
			Value: env.Value,
		}
	}
	return envs
}
