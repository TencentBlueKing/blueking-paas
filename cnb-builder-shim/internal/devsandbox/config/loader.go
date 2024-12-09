package config

import (
	"strings"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

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
	sourceFetchMethod := FetchMethod(utils.EnvOrDefault("SOURCE_FETCH_METHOD", string(HTTP)))
	sourceFetchUrl := utils.EnvOrDefault("SOURCE_FETCH_URL", "")
	gitRevision := utils.EnvOrDefault("GIT_REVISION", "")
	workspace := utils.EnvOrDefault("WORKSPACE", "/cnb/devsandbox/src")

	return SourceCodeConfig{
		FetchMethod: sourceFetchMethod,
		FetchUrl:    sourceFetchUrl,
		GitRevision: gitRevision,
		Workspace:   workspace,
	}, nil
}

func loadCORSConfigFromEnv() (CORSConfig, error) {
	allowOrigins := getListFromEnv("CORS_ALLOW_ORIGINS", "")
	allowMethods := getListFromEnv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS")
	allowHeaders := getListFromEnv("CORS_ALLOW_HEADERS", "Origin,Content-Type,Authorization")
	exposeHeaders := getListFromEnv("CORS_EXPOSE_HEADERS", "Content-Length")
	allowCredentials := utils.EnvOrDefault("CORS_ALLOW_CREDENTIALS", "true") == "true"
	return CORSConfig{
		AllowOrigins:     allowOrigins,
		AllowMethods:     allowMethods,
		AllowHeaders:     allowHeaders,
		ExposeHeaders:    exposeHeaders,
		AllowCredentials: allowCredentials,
	}, nil
}

func loadServiceConfigFromEnv() (ServiceConfig, error) {
	corsConfig, err := loadCORSConfigFromEnv()
	if err != nil {
		return ServiceConfig{}, err
	}
	return ServiceConfig{CORS: corsConfig}, nil
}

func loadConfigFromEnv() (*Config, error) {
	sourceCodeConfig, err := loadSourceConfigFromEnv()
	if err != nil {
		return nil, err
	}

	serviceConfig, err := loadServiceConfigFromEnv()
	if err != nil {
		return nil, err
	}
	return &Config{
		SourceCode: sourceCodeConfig,
		Service:    serviceConfig,
	}, nil
}

// 从指定的环境变量中获取列表, 例如 "value1,value2,value3"
func getListFromEnv(envVar string, defaultEnvValue string) []string {
	// 获取环境变量的值
	listStr := utils.EnvOrDefault(envVar, defaultEnvValue)
	// 使用 "," 分割字符串并去除空格
	elements := strings.Split(listStr, ",")
	for i := range elements {
		elements[i] = strings.TrimSpace(elements[i])
	}
	return elements
}
