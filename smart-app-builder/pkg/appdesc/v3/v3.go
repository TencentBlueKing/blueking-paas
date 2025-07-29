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

// Package v3 provides a shim to parse app_desc v3.
package v3

import (
	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/buildconfig"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// AppDescConfig specVersion: 3 版本的 app_desc
type AppDescConfig struct {
	SpecVersion int          `yaml:"specVersion"`
	AppVersion  string       `yaml:"appVersion"`
	AppInfo     AppInfo      `yaml:"app"`
	Modules     []ModuleSpec `yaml:"modules"`
}

// GetAppCode 获取 app code
func (cfg *AppDescConfig) GetAppCode() string {
	return cfg.AppInfo.AppCode
}

// Validate 验证 app_desc
func (cfg *AppDescConfig) Validate() error {
	if cfg.SpecVersion != 3 {
		return errors.New("spec version must be 3")
	}

	if cfg.AppInfo.AppCode == "" {
		return errors.New("app code is empty")
	}

	if len(cfg.Modules) == 0 {
		return errors.New("modules is empty")
	}

	for _, spec := range cfg.Modules {
		if spec.Spec.Processes == nil {
			return errors.Errorf("processes of module %s is empty", spec.Name)
		}
	}

	return utils.ValidateVersion(cfg.AppVersion)
}

// GenerateProcessCommands 生成各模块进程与启动命令的映射关系. 格式如 {"模块名":{"进程名":"启动命令"}}
func (cfg *AppDescConfig) GenerateProcessCommands() map[string]map[string]string {
	processCommands := make(map[string]map[string]string)

	for _, module := range cfg.Modules {
		commands := make(map[string]string)
		for _, process := range module.Spec.Processes {
			commands[process.Name] = process.ProcCommand
		}
		if len(commands) > 0 {
			processCommands[module.Name] = commands
		}
	}

	return processCommands
}

// GenerateModuleBuildConfig 生成 ModuleBuildConfig
func (cfg *AppDescConfig) GenerateModuleBuildConfig() ([]buildconfig.ModuleBuildConfig, error) {
	config := make([]buildconfig.ModuleBuildConfig, 0)

	for _, module := range cfg.Modules {
		envs := make(map[string]string)
		for _, env := range module.Spec.Configuration.Env {
			envs[env.Name] = env.Value
		}

		// 如果未指定, 表示当前目录
		src := module.SourceDir
		if src == "" {
			src = "."
		}

		buildpacks := module.Spec.Build.Buildpacks
		if buildpacks == nil {
			if bp, err := buildconfig.GetBuildpackByLanguage(module.Language); err != nil {
				return nil, err
			} else {
				buildpacks = []buildconfig.Buildpack{*bp}
			}
		}

		config = append(config, buildconfig.ModuleBuildConfig{
			SourceDir:  src,
			ModuleName: module.Name,
			Envs:       envs,
			Buildpacks: buildpacks,
		})
	}
	return config, nil
}

// AppInfo app 字段
type AppInfo struct {
	AppCode string `yaml:"bkAppCode"`
}

// ModuleSpec 单个 module 字段
type ModuleSpec struct {
	Name      string    `yaml:"name"`
	SourceDir string    `yaml:"sourceDir"`
	Language  string    `yaml:"language"`
	Spec      BkAppSpec `yaml:"spec"`
}

// BkAppSpec bkapp spec
type BkAppSpec struct {
	Processes     []Process               `yaml:"processes"`
	Configuration AppConfig               `yaml:"configuration,omitempty"`
	Build         buildconfig.BuildConfig `yaml:"build,omitempty"`
}

// Process 进程配置
type Process struct {
	// Name of process
	Name string `yaml:"name"`

	// ProcCommand is the script command to start the process
	ProcCommand string `yaml:"procCommand"`
}

// AppConfig is bkapp related configuration, such as environment variables, etc.
type AppConfig struct {
	// List of environment variables to set in the container.
	Env []AppEnvVar `yaml:"env,omitempty"`
}

// AppEnvVar 单个环境变量
type AppEnvVar struct {
	Name  string `yaml:"name"`
	Value string `yaml:"value"`
}
