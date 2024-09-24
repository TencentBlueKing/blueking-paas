package config

import "github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"

var G *Config

func init() {
	cfg, _ := loadConfigFromEnv()

	// 设置全局变量
	G = cfg
}
func loadSourceConfigFromEnv() (SourceCodeConfig, error) {
	sourceFetchMethod := utils.EnvOrDefault("SOURCE_FETCH_METHOD", HTTP)
	sourceGetUrl := utils.EnvOrDefault("SOURCE_GET_URL", "")
	gitRevision := utils.EnvOrDefault("GIT_REVISION", "")
	workspace := utils.EnvOrDefault("WORKSPACE", "/cnb/devsandbox/src")

	return SourceCodeConfig{SourceFetchMethod: sourceFetchMethod, SourceGetUrl: sourceGetUrl, GitRevision: gitRevision, Workspace: workspace}, nil
}

func loadConfigFromEnv() (*Config, error) {
	sourceCodeConfig, err := loadSourceConfigFromEnv()
	if err != nil {
		return nil, err
	}

	return &Config{SourceCode: sourceCodeConfig}, nil
}
