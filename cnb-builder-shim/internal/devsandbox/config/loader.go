package config

import "github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"

var G *Config

func InitConfig() error {
	cfg, err := loadConfigFromEnv()
	if err != nil {
		return err
	}

	// 设置全局变量
	G = cfg
	return nil
}

// 从环境变量中加载配置源码相关配置
func loadSourceConfigFromEnv() (SourceCodeConfig, error) {
	sourceFetchMethod := utils.EnvOrDefault("SOURCE_FETCH_METHOD", HTTP)
	sourceFetchUrl := utils.EnvOrDefault("SOURCE_FETCH_URL", "")
	gitRevision := utils.EnvOrDefault("GIT_REVISION", "")
	workspace := utils.EnvOrDefault("WORKSPACE", "/cnb/devsandbox/src")

	return SourceCodeConfig{SourceFetchMethod: sourceFetchMethod, SourceFetchUrl: sourceFetchUrl, GitRevision: gitRevision, Workspace: workspace}, nil
}

func loadConfigFromEnv() (*Config, error) {
	sourceCodeConfig, err := loadSourceConfigFromEnv()
	if err != nil {
		return nil, err
	}

	return &Config{SourceCode: sourceCodeConfig}, nil
}
