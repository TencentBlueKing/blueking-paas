package v2

import (
	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/buildconfig"
	
)

// AppDescConfig spec_version: 2 版本的 app_desc
type AppDescConfig struct {
	SpecVersion int                   `yaml:"spec_version"`
	AppVersion  string                `yaml:"app_version"`
	AppInfo     AppInfo               `yaml:"app"`
	Modules     map[string]ModuleSpec `yaml:"modules"`
}

// GetAppCode 获取 app code
func (cfg *AppDescConfig) GetAppCode() string {
	return cfg.AppInfo.AppCode
}

// Validate 验证 app_desc
func (cfg *AppDescConfig) Validate() error {
	if cfg.SpecVersion != 2 {
		return errors.New("spec version must be 2")
	}

	if cfg.AppInfo.AppCode == "" {
		return errors.New("app code is empty")
	}

	if len(cfg.Modules) == 0 {
		return errors.New("modules is empty")
	}

	for moduleName, spec := range cfg.Modules {
		if spec.Processes == nil {
			return errors.Errorf("processes of module %s is empty", moduleName)
		}
	}

	return utils.ValidateVersion(cfg.AppVersion)
}

// GenerateProcessCommands 生成各模块进程与启动命令的映射关系. 格式如 {"模块名":{"进程名":"启动命令"}}
func (cfg *AppDescConfig) GenerateProcessCommands() map[string]map[string]string {
	processCommands := make(map[string]map[string]string)

	for moduleName, module := range cfg.Modules {
		commands := make(map[string]string)
		for processName, process := range module.Processes {
			commands[processName] = process.ProcCommand
		}
		if len(commands) > 0 {
			processCommands[moduleName] = commands
		}
	}

	return processCommands
}

// GenerateModuleBuildConfig 生成 ModuleBuildConfig
func (cfg *AppDescConfig) GenerateModuleBuildConfig() ([]buildconfig.ModuleBuildConfig, error) {
	config := make([]buildconfig.ModuleBuildConfig, 0)

	for moduleName, module := range cfg.Modules {
		envs := make(map[string]string)
		for _, env := range module.EnvVariables {
			envs[env.Key] = env.Value
		}

		// 如果未指定, 表示当前目录
		src := module.SourceDir
		if src == "" {
			src = "."
		}

		buildpacks := module.Build.Buildpacks
		if buildpacks == nil {
			if bp, err := buildconfig.GetBuildpackByLanguage(module.Language); err != nil {
				return nil, err
			} else {
				buildpacks = []buildconfig.Buildpack{*bp}
			}
		}

		config = append(config, buildconfig.ModuleBuildConfig{
			SourceDir:  src,
			ModuleName: moduleName,
			Envs:       envs,
			Buildpacks: buildpacks,
		})
	}

	return config, nil
}

// AppInfo app 字段
type AppInfo struct {
	AppCode string `yaml:"bk_app_code"`
}

// ModuleSpec 单个 module 字段
type ModuleSpec struct {
	SourceDir    string                  `yaml:"source_dir"`
	Language     string                  `yaml:"language"`
	Processes    map[string]Process      `yaml:"processes"`
	EnvVariables []AppEnvVar             `yaml:"env_variables,omitempty"`
	Build        buildconfig.BuildConfig `yaml:"build,omitempty"`
}

// Process 进程配置
type Process struct {
	ProcCommand string `yaml:"command"`
}

// AppEnvVar 单个环境变量
type AppEnvVar struct {
	Key   string `yaml:"key"`
	Value string `yaml:"value"`
}
