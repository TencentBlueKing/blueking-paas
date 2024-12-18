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

// EnvV3 ...
type EnvV3 struct {
	Name  string `yaml:"name"`
	Value string `yaml:"value"`
}

// ConfigurationV3 ...
type ConfigurationV3 struct {
	Env []EnvV3 `yaml:"env"`
}

// HooksV3 ...
type HooksV3 struct {
	PreRelease struct {
		ProcCommand string `yaml:"procCommand"`
	} `yaml:"preRelease"`
}

// ProcessV3 ...
type ProcessV3 struct {
	Name        string `yaml:"name"`
	ProcCommand string `yaml:"procCommand"`
}

// SpecV3 ...
type SpecV3 struct {
	Processes     []ProcessV3     `yaml:"processes"`
	Configuration ConfigurationV3 `yaml:"configuration"`
	Hooks         HooksV3         `yaml:"hooks"`
}

// ModuleV3 ...
type ModuleV3 struct {
	Name string `yaml:"name"`
	Spec SpecV3 `yaml:"spec"`
}

// AppDescV3 ...
type AppDescV3 struct {
	SpecVersion string      `yaml:"specVersion"`
	Module      *ModuleV3   `yaml:"module"`
	Modules     []*ModuleV3 `yaml:"modules"`
}

// GetModule returns the ModuleV3 object.
// If Module is not nil, it is returned directly.
// If the moduleName is empty, nil is returned.
// Otherwise, it looks up and returns the module specified by moduleName from the Modules map.
func (a *AppDescV3) GetModule(moduleName string) *ModuleV3 {
	if a.Module != nil {
		return a.Module
	}
	if moduleName == "" {
		return nil
	}
	for _, m := range a.Modules {
		if m.Name == moduleName {
			return m
		}
	}
	return nil
}

// GetProcesses ...
func (a *AppDescV3) GetProcesses() map[string]ProcessV2 {
	module := a.GetModule(moduleName)
	if module == nil {
		return nil
	}
	processes := make(map[string]ProcessV2)
	for _, p := range module.Spec.Processes {
		processes[p.Name] = ProcessV2{
			Command: p.ProcCommand,
		}
	}
	return processes
}

// GetPreReleaseHook ...
func (a *AppDescV3) GetPreReleaseHook() string {
	module := a.GetModule(moduleName)
	if module == nil {
		return ""
	}
	return module.Spec.Hooks.PreRelease.ProcCommand
}

// GetEnvs ...
func (a *AppDescV3) GetEnvs() []EnvV2 {
	module := a.GetModule(moduleName)
	if module == nil {
		return nil
	}
	var envs []EnvV2
	for _, env := range module.Spec.Configuration.Env {
		envs = append(envs, EnvV2{
			Key:   env.Name,
			Value: env.Value,
		})
	}
	return envs
}
