package v3

import (
	"fmt"

	"github.com/pkg/errors"

	bcfg "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/buildconfig"
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
			return fmt.Errorf("processes of module %s is empty", spec.Name)
		}
	}

	return utils.ValidateVersion(cfg.AppVersion)
}

// GenerateProcfile 生成 Procfile
func (cfg *AppDescConfig) GenerateProcfile() map[string]string {
	procfile := make(map[string]string)

	for _, module := range cfg.Modules {
		for _, process := range module.Spec.Processes {
			procfile[module.Name+"-"+process.Name] = process.ProcCommand
		}
	}

	return procfile
}

// GenerateModuleBuildConfig 生成 ModuleBuildConfig
func (cfg *AppDescConfig) GenerateModuleBuildConfig() ([]bcfg.ModuleBuildConfig, error) {
	config := make([]bcfg.ModuleBuildConfig, 0)

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
			if bp, err := bcfg.GetBuildpackByLanguage(module.Language); err != nil {
				return nil, err
			} else {
				buildpacks = []bcfg.Buildpack{*bp}
			}
		}

		config = append(config, bcfg.ModuleBuildConfig{
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
	Processes     []Process        `yaml:"processes"`
	Configuration AppConfig        `yaml:"configuration,omitempty"`
	Build         bcfg.BuildConfig `yaml:"build,omitempty"`
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
