package config

import "github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"

var G *Config

func init() {
	cfg, _ := loadConfigFromEnv()

	// 设置全局变量
	G = cfg
}
func loadSourceConfigFromEnv() (SourceConfig, error) {
	sourceFetchMethod := utils.EnvOrDefault("SOURCE_FETCH_METHOD", HTTP)
	sourceGetUrl := utils.EnvOrDefault("SOURCE_GET_URL", "")
	gitRevision := utils.EnvOrDefault("GIT_REVISION", "")
	uploadDir := utils.EnvOrDefault("UPLOAD_DIR", "/cnb/devsandbox/src")

	return SourceConfig{SourceFetchMethod: sourceFetchMethod, SourceGetUrl: sourceGetUrl, GitRevision: gitRevision, UploadDir: uploadDir}, nil
}

func loadConfigFromEnv() (*Config, error) {
	sourceConfig, err := loadSourceConfigFromEnv()
	if err != nil {
		return nil, err
	}

	return &Config{Source: sourceConfig}, nil
}
