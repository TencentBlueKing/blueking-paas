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
	"net/url"
	"os"
	"path/filepath"
	"strings"

	"github.com/go-logr/logr"
	"github.com/pelletier/go-toml/v2"
	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/config"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/fs"
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

func sourceInit() error {
	logger.Info(fmt.Sprintf("Downloading source code to %s...", config.G.Source.SourceFetchMethod))
	switch config.G.Source.SourceFetchMethod {
	case config.BKREPO:
		downloadUrl, err := url.Parse(config.G.Source.SourceGetUrl)
		if err != nil {
			return err
		}
		if err = fs.NewFetcher(logger).Fetch(downloadUrl.Path, config.G.Source.UploadDir); err != nil {
			return err
		}
	case config.GIT:
		return fmt.Errorf("TODO: clone git from revision")
	}
	return nil
}
