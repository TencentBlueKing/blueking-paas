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

// Package builder ...
package builder

import (
	"net/url"
	"os"

	"github.com/go-logr/logr"
	"github.com/pkg/errors"

	fetchFs "github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/fs"
	fetchHttp "github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/http"

	bexec "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/executor"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/plan"
	putFs "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/putter/fs"
	putHttp "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/putter/http"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// AppBuilder build the source code to artifact
type AppBuilder struct {
	sourceURL string
	destURL   string
	executor  BuildExecutor

	logger logr.Logger
}

// Build run build process
func (a *AppBuilder) Build() error {
	appDir := a.executor.GetAppDir()

	// 获取源码
	if err := a.fetchSource(appDir); err != nil {
		return err
	}

	// 准备构建计划
	buildPlan, err := plan.PrepareBuildPlan(appDir)
	if err != nil {
		return err
	}

	// 执行构建, 生成 artifact
	artifactTGZ, err := a.executor.Build(buildPlan)
	if err != nil {
		return err
	}

	return a.pushArtifact(artifactTGZ)
}

// fetchSource fetch the source code to destDir
func (a *AppBuilder) fetchSource(destDir string) error {
	parsedURL, err := url.Parse(a.sourceURL)
	if err != nil {
		return err
	}

	switch parsedURL.Scheme {
	case "file":
		// TODO 重构 cnb-builder-shim/pkg/fetcher/fs 以支持非压缩文件, 简化此处代码
		filePath := parsedURL.Path

		fileInfo, err := os.Stat(filePath)
		if err != nil {
			return err
		}

		if !fileInfo.IsDir() {
			if err = fetchFs.NewFetcher(a.logger).Fetch(filePath, destDir); err != nil {
				return err
			} else {
				return nil
			}
		}

		// 如果是文件目录, 目录不同时, 直接将源码拷贝到 destDir 下
		if filePath != destDir {
			return utils.CopyDir(filePath, destDir)
		}
		return nil

	case "http", "https":
		if err := fetchHttp.NewFetcher(a.logger).Fetch(a.sourceURL, destDir); err != nil {
			return err
		}
	default:
		return errors.Errorf("not support source-url scheme: %s", parsedURL.Scheme)
	}

	return nil
}

func (a *AppBuilder) pushArtifact(artifactTGZ string) error {
	parsedURL, err := url.Parse(a.destURL)
	if err != nil {
		return errors.Errorf("destURL parse error")
	}

	switch parsedURL.Scheme {
	case "file":
		return putFs.NewPutter(a.logger).Put(artifactTGZ, parsedURL)

	case "http", "https":
		return putHttp.NewPutter(a.logger).Put(artifactTGZ, parsedURL)
	default:
		return errors.Errorf("not support dest-url scheme: %s", parsedURL.Scheme)
	}
}

// BuildExecutor is the interface which execute the build process
type BuildExecutor interface {
	// GetAppDir return the source code directory
	GetAppDir() string
	// Build will build the source code by plan, return the artifact({app_code}.tgz) file path
	Build(buildPlan *plan.BuildPlan) (string, error)
}

// New returns a AppBuilder instance
func New(logger logr.Logger, sourceURL, destURL string) (*AppBuilder, error) {
	if executor, err := bexec.NewContainerExecutor(); err != nil {
		return nil, err
	} else {
		return &AppBuilder{logger: logger, sourceURL: sourceURL, destURL: destURL, executor: executor}, nil
	}
}
