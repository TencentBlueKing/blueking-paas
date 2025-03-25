package main

import (
	"fmt"
	"os"

	"github.com/spf13/pflag"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/config"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

const (
	SourceURLEnvVarKey = "SOURCE_GET_URL"
	DestURLEnvVarKey   = "DEST_PUT_URL"
)

func main() {
	logger := utils.GetLogger()

	executor, err := builder.NewBuildExecutor(logger, config.G.SourceURL, config.G.DestURL)
	if err != nil {
		logger.Error(err, "failed to create build executor")
		os.Exit(1)
	}

	logger.Info("start to build s-mart package")

	if err := executor.Execute(); err != nil {
		logger.Error(err, "failed to build s-mart package")
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
			fmt.Errorf("sourceURL is empty"),
			fmt.Sprintf(
				"please provide by setting --source-url option or setting as an environment variable %s",
				SourceURLEnvVarKey,
			),
		)
		os.Exit(1)
	}

	if config.G.DestURL == "" {
		logger.Error(
			fmt.Errorf("destURL is empty"),
			fmt.Sprintf(
				"please provide by setting --dest-url option or setting as an environment variable %s",
				DestURLEnvVarKey,
			),
		)
		os.Exit(1)
	}
}
