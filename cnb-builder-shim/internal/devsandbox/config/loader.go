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

// Package config ...
package config

import (
	"strings"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

// G is the global config
var G *Config

// Init 初始化配置
func Init() error {
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

func loadModuleNameFromEnv() (string, error) {
	return utils.EnvOrDefault("BKPAAS_APP_MODULE_NAME", ""), nil
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

	moduleName, err := loadModuleNameFromEnv()
	if err != nil {
		return nil, err
	}
	return &Config{
		SourceCode: sourceCodeConfig,
		Service:    serviceConfig,
		ModuleName: moduleName,
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
