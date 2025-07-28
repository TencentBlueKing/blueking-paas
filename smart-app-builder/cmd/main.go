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

package main

import (
	"fmt"
	"os"

	"github.com/pkg/errors"
	"github.com/spf13/pflag"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/config"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

const (
	SourceURLEnvVarKey = "SOURCE_GET_URL"
	DestURLEnvVarKey   = "DEST_PUT_URL"
)

func main() {
	logger := utils.GetLogger()

	appBuilder, err := builder.New(logger, config.G.SourceURL, config.G.DestURL)
	if err != nil {
		logger.Error(err, "create app builder")
		os.Exit(1)
	}

	logger.Info("start to build s-mart package")

	if err := appBuilder.Build(); err != nil {
		logger.Error(err, "build s-mart package")
		os.Exit(1)
	}

	logger.Info("build s-mart package successfully")
}

func init() {
	pflag.String(
		"source-url",
		os.Getenv(SourceURLEnvVarKey),
		"The url of the source code, which begins with file:// or http(s)://",
	)
	pflag.String(
		"dest-url",
		os.Getenv(DestURLEnvVarKey),
		"The url of the s-mart artifact to put, which begins with file:// or http(s)://",
	)

	pflag.Parse()

	// 设置全局配置
	config.SetGlobalConfig()

	logger := utils.GetLogger()

	if config.G.SourceURL == "" {
		logger.Error(
			errors.New("sourceURL is empty"),
			fmt.Sprintf(
				"please provide by setting --source-url option or setting as an environment variable %s",
				SourceURLEnvVarKey,
			),
		)
		os.Exit(1)
	}

	if config.G.DestURL == "" {
		logger.Error(
			errors.New("destURL is empty"),
			fmt.Sprintf(
				"please provide by setting --dest-url option or setting as an environment variable %s",
				DestURLEnvVarKey,
			),
		)
		os.Exit(1)
	}
}
