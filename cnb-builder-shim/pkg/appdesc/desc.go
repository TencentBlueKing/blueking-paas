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

import (
	"fmt"
	"os"
	"strings"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v3"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

var appSpecVersion2 = "2"
var appSpecVersion3 = "3"
var moduleName = utils.EnvOrDefault("BKPAAS_APP_MODULE_NAME", "")

// AppDesc ...
type AppDesc interface {
	// GetProcesses gets the list of processes, for compatibility
	// it is expressed in the form of Process in the V2 version.
	GetProcesses() map[string]ProcessV2
	// GetPreReleaseHook get hooks command
	GetPreReleaseHook() string
	// GetEnvs get environment variables, for compatibility
	// it is expressed as Env in V2 version
	GetEnvs() []EnvV2
}

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
func (a *AppDescV2) GetModule() *ModuleV2 {
	if a.Module != nil {
		return a.Module
	}
	if moduleName == "" {
		return nil
	}
	return a.Modules[moduleName]
}

// GetProcesses ...
func (a *AppDescV2) GetProcesses() map[string]ProcessV2 {
	module := a.GetModule()
	if module == nil {
		return nil
	}
	return module.Processes
}

// GetPreReleaseHook ...
func (a *AppDescV2) GetPreReleaseHook() string {
	module := a.GetModule()
	if module == nil {
		return ""
	}
	return module.Scripts.PreReleaseHook
}

// GetEnvs ...
func (a *AppDescV2) GetEnvs() []EnvV2 {
	module := a.GetModule()
	if module == nil {
		return nil
	}
	return module.ProcEnvs
}

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
func (a *AppDescV3) GetModule() *ModuleV3 {
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
	module := a.GetModule()
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
	module := a.GetModule()
	if module == nil {
		return ""
	}
	return module.Spec.Hooks.PreRelease.ProcCommand
}

// GetEnvs ...
func (a *AppDescV3) GetEnvs() []EnvV2 {
	module := a.GetModule()
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

// AppSpecVersions ...
type AppSpecVersions struct {
	AppSpecVersion2 string `yaml:"spec_version"`
	AppSpecVersion3 string `yaml:"specVersion"`
}

// GetAppSpec gets the corresponding AppDesc based on spec_version.
func (a *AppSpecVersions) GetAppSpec() (AppDesc, error) {
	if a.AppSpecVersion2 == appSpecVersion2 {
		return new(AppDescV2), nil
	} else if a.AppSpecVersion3 == appSpecVersion3 {
		return new(AppDescV3), nil
	}
	return nil, errors.New("invalid app spec version")
}

// UnmarshalToAppDesc reads from the given app_desc.yaml and unmarshals it into an AppDesc struct.
// Compatible with v2 and v3 versions of app_desc.yaml
func UnmarshalToAppDesc(descFilePath string) (AppDesc, error) {
	yamlFile, err := os.ReadFile(descFilePath)
	if err != nil {
		return nil, errors.Wrap(err, "failed to read app desc file")
	}
	appSpecVersions := new(AppSpecVersions)
	if err = yaml.Unmarshal(yamlFile, appSpecVersions); err != nil {
		return nil, errors.Wrap(err, "failed to unmarshal app spec versions")
	}
	desc, err := appSpecVersions.GetAppSpec()
	if err != nil {
		return nil, err
	}

	if err = yaml.Unmarshal(yamlFile, desc); err != nil {
		return nil, errors.Wrap(err, "failed to unmarshal app desc")
	}
	return desc, nil
}

// TransformToProcfile transforms an app_desc.yaml file into a Procfile string.
//
// It takes a path to an app_desc.yaml file as input and returns a string
// representation of a Procfile.
func TransformToProcfile(descFilePath string) (string, error) {
	desc, err := UnmarshalToAppDesc(descFilePath)
	if err != nil {
		return "", err
	}

	lines := []string{}
	for pType, p := range desc.GetProcesses() {
		lines = append(lines, fmt.Sprintf("%s: %s", pType, p.Command))
	}

	return strings.Join(lines, "\n"), nil
}
