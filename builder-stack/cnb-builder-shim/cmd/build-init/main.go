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
	"io/ioutil"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	"github.com/go-logr/logr"
	"github.com/google/go-containerregistry/pkg/authn"
	"github.com/pelletier/go-toml/v2"
	"github.com/pkg/errors"
	flag "github.com/spf13/pflag"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/dockercreds"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/fs"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/http"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
)

const (
	appDir      = "/app"
	platformDir = "/platform"
	cnbDir      = "/cnb"

	// OutputImageEnvVarKey The env var key that store output image
	OutputImageEnvVarKey = "OUTPUT_IMAGE"
	// RunImageEnvVarKey The env var key that store runner image
	RunImageEnvVarKey = "RUN_IMAGE"
	// SourceUrlEnvVarKey The env var key that store source url
	SourceUrlEnvVarKey = "SOURCE_GET_URL"
	// GitRevisionEnvVarKey The env var key that store git revision info
	GitRevisionEnvVarKey = "GIT_REVISION"
	// RequiredBuildpacksEnvVarKey The env var key that store required buildpacks info
	RequiredBuildpacksEnvVarKey = "REQUIRED_BUILDPACKS"

	// DefaultUid is the default uid to run lifecycle
	DefaultUid int = 2000
	// DefaultGid is the default gid to run lifecycle
	DefaultGid int = 2000
)

var (
	outputImage = flag.String("output-image", os.Getenv(OutputImageEnvVarKey), "The name of image that will get created by the lifecycle.")
	runImage    = flag.String("run-image", os.Getenv(RunImageEnvVarKey), "The base image from which application images are built.")

	buildpacks = flag.String("buildpacks", os.Getenv(RequiredBuildpacksEnvVarKey), "Those buildpacks that will used by the lifecycle.")

	sourceUrl   = flag.String("source-url", os.Getenv(SourceUrlEnvVarKey), "The url of the source code.")
	gitRevision = flag.String("git-revision", os.Getenv(GitRevisionEnvVarKey), "The Git revision to make the repository HEAD.")

	uid = flag.Int("uid", DefaultUid, "UID of user's group in the stack's build and run images")
	gid = flag.Int("gid", DefaultGid, "GID of user's group in the stack's build and run images")
)

func init() {
	flag.Lookup("git-revision").NoOptDefVal = "master"
}

func main() {
	flag.Parse()
	logger := logging.Default()
	if *outputImage == "" {
		logger.Error(
			fmt.Errorf("outputImage is empty"),
			fmt.Sprintf("please provide outputImage by --output-image or env variable %s", OutputImageEnvVarKey),
		)
		os.Exit(1)
	}
	if *runImage == "" {
		logger.Error(
			fmt.Errorf("runImage is empty"),
			fmt.Sprintf("please provide it by using --run-image or setting it as an environment variable %s", RunImageEnvVarKey),
		)
		os.Exit(1)
	}
	if *sourceUrl == "" {
		logger.Error(
			fmt.Errorf("sourceUrl is empty"),
			fmt.Sprintf("please provide it by using --source-url or setting it as an environment variable %s", SourceUrlEnvVarKey),
		)
		os.Exit(1)
	}

	var (
		keychain authn.Keychain
		err      error
	)
	logger.Info("Setup Build Environ")
	logger.Info("Loading registry credentials...")
	if keychain, err = dockercreds.DefaultKeychain(); err != nil {
		logger.Error(err, "Failed to load registry credentials")
		os.Exit(1)
	}

	logger.Info("Verifying accessibility to container image registry...")
	if err = verifyOutputImageWritable(keychain); err != nil {
		logger.Error(err, "OutputImage is not writable")
		os.Exit(1)
	}
	if err = verifyRunImageReadable(keychain); err != nil {
		logger.Error(err, "RunImage is not readable")
		os.Exit(1)
	}

	logger.Info("Initializing platform env...")
	if err = setupPlatformEnv(logger, platformDir, os.Environ()); err != nil {
		logger.Error(err, "Failed to setup platform env")
		os.Exit(1)
	}

	logger.Info("Setting buildpacks execute order...")
	if err = setupBuildpacksOrder(logger, *buildpacks, cnbDir); err != nil {
		logger.Error(err, "Failed to set buildpacks execute order")
		os.Exit(1)
	}

	logger.Info("Fetching source code...")
	if err = fetchSource(logger, appDir); err != nil {
		logger.Error(err, "Failed to fetch source code")
		os.Exit(1)
	}
	if err = ChownR(appDir, *uid, *gid); err != nil {
		logger.Error(err, "Failed to ChownR")
		os.Exit(1)
	}
}

// fetchSource: 拉取源码
func fetchSource(logger logr.Logger, appDir string) error {
	url, err := url.Parse(*sourceUrl)
	if err != nil {
		return err
	}
	switch url.Scheme {
	case "file":
		if err := fs.NewFetcher(logger).Fetch(url.Path, appDir); err != nil {
			return err
		}
	case "http", "https":
		if err := http.NewFetcher(logger).Fetch(*sourceUrl, appDir); err != nil {
			return err
		}
	case "git":
		return fmt.Errorf("TODO: clone git from revision %s", *gitRevision)
	default:
		return errors.New("invalid source url")
	}
	return nil
}

// setupPlatformEnv: 初始化 build 阶段可使用的环境变量
// 基于 lifecycle 协议, build 阶段的环境变量需要将环境变量按文件写入到 /platform/env 目录
func setupPlatformEnv(logger logr.Logger, platformDir string, env []string) error {
	err := os.MkdirAll(filepath.Join(platformDir, "env"), 0744)
	if err != nil {
		return errors.Wrap(err, "failed to create env dir")
	}
	var ignoredEnvs = map[string]interface{}{
		dockercreds.EnvRegistryAuth: nil,
		OutputImageEnvVarKey:        nil,
		RunImageEnvVarKey:           nil,
		SourceUrlEnvVarKey:          nil,
		GitRevisionEnvVarKey:        nil,
		"S3CMD_CONF":                nil,
		"BKREPO_CONF":               nil,
		"CACHE_PATH":                nil,
		"CACHE_GET_URL":             nil,
		"CACHE_SET_URL":             nil,
		"TAR_PATH":                  nil,
		"PUT_PATH":                  nil,
		"SOURCE_SET_URL":            nil,
		"SLUG_URL":                  nil,
		"SLUG_GET_URL":              nil,
		"PILOT_SENTRY_DSN":          nil,
	}
	for _, e := range env {
		pair := strings.SplitN(e, "=", 2)
		key, val := pair[0], pair[1]
		if _, ok := ignoredEnvs[key]; ok {
			logger.V(2).Info(fmt.Sprintf("skip env var %s", key))
		} else {
			err := ioutil.WriteFile(filepath.Join(platformDir, "env", key), []byte(val), 0755)
			if err != nil {
				return errors.Wrapf(err, "failed to write env var %s", key)
			}
		}
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

// setupBuildpacksOrder: 根据环境变量设置 buildpacks 的执行顺序
func setupBuildpacksOrder(logger logr.Logger, buildpacks string, cnbDir string) error {
	err := os.MkdirAll(cnbDir, 0744)
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
	var order = Order{
		Order: []Group{group},
	}
	data, err := toml.Marshal(order)
	if err != nil {
		return errors.Wrap(err, "failed to marshal order")
	}
	err = ioutil.WriteFile(filepath.Join(cnbDir, "order.toml"), data, 0755)
	if err != nil {
		return errors.Wrap(err, "failed to write order.toml")
	}
	return nil
}

// verifyOutputImageWritable: 测试是否具有 output image 镜像的写权限
func verifyOutputImageWritable(keychain authn.Keychain) error {
	if err := dockercreds.VerifyWriteAccess(keychain, *outputImage); err != nil {
		return errors.Wrapf(err, "Error verifying write access to %q", *outputImage)
	}
	return nil
}

// verifyRunImageReadable: 测试 run image 镜像存在且具有读权限
func verifyRunImageReadable(keychain authn.Keychain) error {
	if err := dockercreds.VerifyReadAccess(keychain, *runImage); err != nil {
		return errors.Wrapf(err, "Error verifying read access to run image %q", *runImage)
	}
	return nil
}

// ChownR changes the numeric uid and gid of all files in path.
func ChownR(path string, uid, gid int) error {
	return filepath.Walk(path, func(name string, info os.FileInfo, err error) error {
		if err == nil {
			err = os.Chown(name, uid, gid)
		}
		return err
	})
}
