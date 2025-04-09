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
	"path"
	"path/filepath"
	"strings"

	"github.com/go-logr/logr"
	"github.com/google/go-containerregistry/pkg/authn"
	"github.com/pelletier/go-toml/v2"
	"github.com/pkg/errors"
	flag "github.com/spf13/pflag"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/buildpack"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/dockercreds"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/fs"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/http"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

const (
	appDir      = "/app"
	platformDir = "/platform"
	cnbDir      = "/cnb"

	// CacheImageEnvVarKey The env var key that store cache image
	CacheImageEnvVarKey = "CACHE_IMAGE"
	// OutputImageEnvVarKey The env var key that store output image
	OutputImageEnvVarKey = "OUTPUT_IMAGE"
	// RunImageEnvVarKey The env var key that store runner image
	RunImageEnvVarKey = "CNB_RUN_IMAGE"
	// UseDockerDaemonEnvVarKey The env var key that store a flag meaning if use docker daemon
	UseDockerDaemonEnvVarKey = "USE_DOCKER_DAEMON"
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

	// SkipTLSVerifyEnvVarKey The env var key that store SkipTLSVerify
	SkipTLSVerifyEnvVarKey = "CNB_SKIP_TLS_VERIFY"
)

var (
	cacheImage  = flag.String("cache-image", os.Getenv(CacheImageEnvVarKey), "cache image tag name.")
	outputImage = flag.String("output-image", os.Getenv(OutputImageEnvVarKey), "The name of image that will get created by the lifecycle.")
	runImage    = flag.String("run-image", os.Getenv(RunImageEnvVarKey), "The base image from which application images are built.")
	useDaemon   = flag.Bool("daemon", utils.BoolEnv(UseDockerDaemonEnvVarKey), "export image to docker daemon.")

	buildpacks = flag.String("buildpacks", os.Getenv(RequiredBuildpacksEnvVarKey), "Those buildpacks that will used by the lifecycle.")

	sourceUrl   = flag.String("source-url", os.Getenv(SourceUrlEnvVarKey), "The url of the source code.")
	gitRevision = flag.String("git-revision", os.Getenv(GitRevisionEnvVarKey), "The Git revision to make the repository HEAD.")

	uid = flag.Int("uid", DefaultUid, "UID of user's group in the stack's build and run images.")
	gid = flag.Int("gid", DefaultGid, "GID of user's group in the stack's build and run images.")

	skipTLSVerify = flag.Bool("skip-tls-verify",
		utils.BoolEnv(SkipTLSVerifyEnvVarKey),
		"Skip verify TLS certificates.")
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
	if *skipTLSVerify {
		dockercreds.InsecureSkipVerify()
	}

	var err error
	logger.Info("Setup Build Environ")
	logger.Info("Loading registry credentials...")
	keychain := dockercreds.DefaultKeychain()

	if !*useDaemon {
		logger.Info("Verifying accessibility to container image registry...")
		if err = verifyOutputImageWritable(keychain); err != nil {
			logger.Error(err, "OutputImage is not writable")
			os.Exit(1)
		}
		if err = verifyRunImageReadable(keychain); err != nil {
			logger.Error(err, "RunImage is not readable")
			os.Exit(1)
		}
	}

	// 目前 lifecycle 只支持导出 cache image 到 registry
	if *cacheImage != "" {
		logger.Info("Verifying accessibility to cache registry...")
		if err = verifyCacheImageWritable(keychain); err != nil {
			logger.Error(err, "CacheImage is not writable")
			os.Exit(1)
		}
	}

	logger.Info("Initializing platform env...")
	if err = setupPlatformEnv(logger, platformDir, os.Environ()); err != nil {
		logger.Error(err, "Failed to setup platform env")
		os.Exit(1)
	}

	logger.Info("Setup buildpacks...")
	if err = setupBuildpacks(logger, *buildpacks, cnbDir); err != nil {
		logger.Error(err, "Failed to setup buildpacks")
		os.Exit(1)
	}

	logger.Info("Fetching source code...")
	if err = fetchSource(logger, appDir); err != nil {
		logger.Error(err, "Failed to fetch source code")
		os.Exit(1)
	}
	if err = chownR(appDir, *uid, *gid); err != nil {
		logger.Error(err, "Failed to ChownR")
		os.Exit(1)
	}
}

// 拉取应用源代码
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

// 初始化 build 阶段可使用的环境变量
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
			err := os.WriteFile(filepath.Join(platformDir, "env", key), []byte(val), 0755)
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

// 根据环境变量设置 buildpacks 的执行顺序，若发现某 buildpack 声明为远程，则下载并解压到 /cnb/buildpacks 目录
func setupBuildpacks(logger logr.Logger, buildpacks string, cnbDir string) error {
	if err := os.MkdirAll(cnbDir, 0744); err != nil {
		return errors.Wrap(err, "failed to create cnb dir")
	}

	var group Group
	for _, bp := range strings.Split(buildpacks, ";") {
		// buildpack 的格式为:
		// oci-image bk-buildpack-apt urn:cnb:registry:fagiani/apt v2
		// oci-embedded bk-buildpack-python blueking/python v213
		// tar bk-buildpack-go http://bkrepo.example.com/buildpacks/bk-buildpack-go.tgz v205
		items := strings.SplitN(bp, " ", 4)
		if len(items) != 4 {
			logger.Info("Invalid buildpack config", "bp", bp)
			continue
		}

		bpType, bpName, bpUrl, bpVersion := items[0], items[1], items[2], items[3]

		// 目前按约定，仅支持下载 tgz 类型的 buildpack，其是适配云原生 builder 的
		// 注：不支持下载 tar 是避免下载到 slug-pilot 使用的，历史版本的 buildpack
		if bpType == buildpack.TypeTgz {
			destDir := path.Join(cnbDir, bpName, bpVersion)
			// 如果目标目录已经存在，则先清理再下载远程 buildpack（覆盖）
			if _, err := os.Stat(destDir); err == nil {
				logger.Info("Overwritten directory with remote buildpack", "destDir", destDir)

				if err = os.RemoveAll(destDir); err != nil {
					return errors.Wrapf(err, "failed to remove dir %s", destDir)
				}
			}

			// 下载远程 buildpack 并解压到指定目录
			logger.Info("Downloading remote buildpack...", "url", bpUrl, "destDir", destDir)
			if err := http.NewFetcher(logger).Fetch(bpUrl, destDir); err != nil {
				return err
			}
		}

		group.Group = append(group.Group, GroupElement{ID: bpName, Version: bpVersion})
	}

	data, err := toml.Marshal(Order{Order: []Group{group}})
	if err != nil {
		return errors.Wrap(err, "failed to marshal order")
	}
	err = os.WriteFile(filepath.Join(cnbDir, "order.toml"), data, 0755)
	if err != nil {
		return errors.Wrap(err, "failed to write order.toml")
	}
	return nil
}

// 测试是否具有 output image 镜像的写权限
func verifyOutputImageWritable(keychain authn.Keychain) error {
	if err := dockercreds.VerifyWriteAccess(keychain, *outputImage); err != nil {
		return errors.Wrapf(err, "Error verifying write access to %q", *outputImage)
	}
	return nil
}

// 测试是否具有 output image 镜像的写权限
func verifyCacheImageWritable(keychain authn.Keychain) error {
	if err := dockercreds.VerifyWriteAccess(keychain, *cacheImage); err != nil {
		return errors.Wrapf(err, "Error verifying write access to %q", *cacheImage)
	}
	return nil
}

// 测试 run image 镜像存在且具有读权限
func verifyRunImageReadable(keychain authn.Keychain) error {
	if err := dockercreds.VerifyReadAccess(keychain, *runImage); err != nil {
		return errors.Wrapf(err, "Error verifying read access to run image %q", *runImage)
	}
	return nil
}

// changes the numeric uid and gid of all files in path.
func chownR(path string, uid, gid int) error {
	return filepath.Walk(path, func(name string, info os.FileInfo, err error) error {
		if err == nil {
			err = os.Chown(name, uid, gid)
		}
		return err
	})
}
