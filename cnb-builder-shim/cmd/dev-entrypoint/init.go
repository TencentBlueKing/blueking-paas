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
	"path/filepath"
	"strings"

	"github.com/go-logr/logr"
	"github.com/pelletier/go-toml/v2"
	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/config"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/vcs"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/http"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

const (
	platformDir = "/platform"
	cnbDir      = "/cnb"
	// RequiredBuildpacksEnvVarKey The env var key that store required buildpacks info
	RequiredBuildpacksEnvVarKey = "REQUIRED_BUILDPACKS"
)

func buildInit() error {
	var err error

	logger.Info("Initializing platform env...")
	if err = setupPlatformEnv(logger, platformDir, os.Environ()); err != nil {
		return errors.Wrap(err, "Failed to setup platform env")
	}

	logger.Info("Setting buildpacks execute order...")
	if err = setupBuildpacksOrder(logger, utils.EnvOrDefault(RequiredBuildpacksEnvVarKey, ""), cnbDir); err != nil {
		return errors.Wrap(err, "Failed to set buildpacks execute order")
	}

	return nil
}

// Order ...
type Order struct {
	Order []Group `toml:"order"`
}

// Group ...
type Group struct {
	Group []GroupElement `toml:"group"`
}

// A GroupElement represents a buildpack referenced in a buildpack.toml's [[order.group]] OR
// a buildpack or extension in order.toml OR a buildpack or extension in group.toml.
type GroupElement struct {
	// ID specifies the ID of the buildpack or extension.
	ID string `toml:"id" json:"id"`
	// Version specifies the version of the buildpack or extension.
	Version string `toml:"version" json:"version"`

	// Optional specifies that the buildpack or extension is optional. Extensions are always optional.
	Optional bool `toml:"optional,omitempty" json:"optional,omitempty"`
}

// setupPlatformEnv: 初始化 build 阶段可使用的环境变量
// 基于 lifecycle 协议, build 阶段的环境变量需要将环境变量按文件写入到 /platform/env 目录
func setupPlatformEnv(logger logr.Logger, platformDir string, env []string) error {
	err := os.MkdirAll(filepath.Join(platformDir, "env"), 0o744)
	if err != nil {
		return errors.Wrap(err, "failed to create env dir")
	}
	ignoredEnvs := map[string]interface{}{}
	for _, e := range env {
		pair := strings.SplitN(e, "=", 2)
		key, val := pair[0], pair[1]
		if _, ok := ignoredEnvs[key]; ok {
			logger.V(2).Info(fmt.Sprintf("skip env var %s", key))
		} else {
			err = os.WriteFile(filepath.Join(platformDir, "env", key), []byte(val), 0o755)
			if err != nil {
				return errors.Wrapf(err, "failed to write env var %s", key)
			}
		}
	}
	return nil
}

// setupBuildpacksOrder: 根据环境变量设置 buildpacks 的执行顺序
func setupBuildpacksOrder(logger logr.Logger, buildpacks string, cnbDir string) error {
	err := os.MkdirAll(cnbDir, 0o744)
	if err != nil {
		return errors.Wrap(err, "failed to create cnb dir")
	}
	parts := strings.Split(buildpacks, ";")
	var group Group
	for _, part := range parts {
		items := strings.SplitN(part, " ", 4)
		if len(items) < 4 || len(items) > 5 {
			logger.V(2).Info("Invalid buildpack config", "bp", part)
			continue
		}

		bpName := items[1]
		version := items[3]
		group.Group = append(group.Group, GroupElement{
			ID:      bpName,
			Version: version,
		})
	}
	order := Order{
		Order: []Group{group},
	}
	data, err := toml.Marshal(order)
	if err != nil {
		return errors.Wrap(err, "failed to marshal order")
	}
	err = os.WriteFile(filepath.Join(cnbDir, "order.toml"), data, 0o755)
	if err != nil {
		return errors.Wrap(err, "failed to write order.toml")
	}
	return nil
}

// initializeSourceCode: 根据配置初始化源码
func initializeSourceCode() error {
	workspace := config.G.SourceCode.Workspace
	logger.Info(fmt.Sprintf("Downloading source code to %s...", workspace))
	// TODO: 源码初始化不同的方式抽象成一个接口
	// 确保工作空间存在
	if err := ensureWorkspace(workspace); err != nil {
		return err
	}
	// 检查 workspace 下是否已经有文件
	codeExists, err := fileExists(workspace)
	if err != nil {
		return err
	}
	// 源码已经下载到工作目录，无需初始化
	if codeExists {
		return nil
	}
	switch config.G.SourceCode.FetchMethod {
	case config.BK_REPO:
		// 下载源码
		if err = http.NewFetcher(logger).Fetch(config.G.SourceCode.FetchUrl, workspace); err != nil {
			return errors.Wrap(err, "download source code")
		}
		// 修改目录权限
		if err = utils.SetFullPermissions(workspace); err != nil {
			return errors.Wrap(err, "chmod files")
		}
	case config.GIT:
		return fmt.Errorf("TODO: clone git from revision")
	}

	// 初始化版本控制器
	if err = vcs.New().Prepare(workspace); err != nil {
		return errors.Wrap(err, "version controller preparing")
	}
	return nil
}

// ensureWorkspace 确保 workspace 文件夹存在，如果不存在则创建该文件夹
func ensureWorkspace(workspace string) (err error) {
	// 检查文件夹是否存在
	if _, err = os.Stat(workspace); os.IsNotExist(err) {
		// 文件夹不存在，创建文件夹
		logger.Info("create workspace directory")
		if err = os.MkdirAll(workspace, 0750); err != nil {
			return errors.Wrap(err, "create workspace directory")
		}
		return nil
	}
	return err
}

// fileExists 判断文件夹是否存在文件
func fileExists(path string) (exists bool, err error) {
	// 文件夹存在，检查文件夹里面是否有文件
	files, err := os.ReadDir(path)
	if err != nil {
		return false, errors.Wrap(err, "read workspace directory")
	}

	return len(files) > 0, nil
}
