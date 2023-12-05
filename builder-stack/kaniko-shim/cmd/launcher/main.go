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
	"context"
	"encoding/base64"
	"fmt"
	"io/ioutil"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/go-logr/logr"
	"github.com/pkg/errors"
	flag "github.com/spf13/pflag"

	"github.com/TencentBlueking/bkpaas/kaniko-shim/pkg/fetcher/fs"
	"github.com/TencentBlueking/bkpaas/kaniko-shim/pkg/fetcher/http"
	"github.com/TencentBlueking/bkpaas/kaniko-shim/pkg/logging"
	"github.com/TencentBlueking/bkpaas/kaniko-shim/pkg/utils"
)

const (
	// BuildContextDir The path that kaniko read build context
	BuildContextDir = "/workspace/"
	// DockerConfigJsonPath The path that kaniko read docker credentials
	DockerConfigJsonPath = "/kaniko/.docker/config.json"
	// DefaultDockerfile default dockerfile
	DefaultDockerfile = "Dockerfile"
	// DefaultSourceUrl default url that can fetch source code
	DefaultSourceUrl = "file:///tmp/context.tar.gz"

	// DockerfileEnvVarKey The env var key that store DockerfilePath
	DockerfileEnvVarKey = "DOCKERFILE_PATH"
	// BuildArgEnvVarKey The env var key that store build-arg pairs
	BuildArgEnvVarKey = "BUILD_ARG"
	// OutputImageEnvVarKey The env var key that store output image
	OutputImageEnvVarKey = "OUTPUT_IMAGE"
	// SourceUrlEnvVarKey The env var key that store source url
	SourceUrlEnvVarKey = "SOURCE_GET_URL"
	// DockerConfigJsonEnvVarKey The env var key that store based64 encoded docker config json
	DockerConfigJsonEnvVarKey = "DOCKER_CONFIG_JSON"
	// CacheRepoEnvVarKey The env var key that store cache repo
	CacheRepoEnvVarKey = "CACHE_REPO"
	// InsecureRegistriesEnvVarKey The env var key that store InsecureRegistries
	InsecureRegistriesEnvVarKey = "InsecureRegistries"
	// SkipTLSVerifyRegistriesEnvVarKey The env var key that store SkipTlsVerifyRegistries
	SkipTLSVerifyRegistriesEnvVarKey = "SkipTlsVerifyRegistries"
)

var (
	dockerfilePath = flag.String("dockerfile",
		os.Getenv(DockerfileEnvVarKey),
		"Path to the dockerfile to be built.")
	buildArgs = flag.String("build-arg",
		os.Getenv(BuildArgEnvVarKey),
		"This flag allows you to pass in ARG values at build time. Set it repeatedly for multiple values.")

	outputImage = flag.String("output-image",
		os.Getenv(OutputImageEnvVarKey),
		"The name of image that will get created by the kaniko.")
	cacheRepo = flag.String("cache-repo",
		os.Getenv(CacheRepoEnvVarKey),
		"Specify a repository to use as a cache, otherwise one will be inferred from the destination provided; "+
			"when prefixed with 'oci:' the repository will be written in OCI image layout format at the path provided")

	sourceUrl = flag.String("source-url",
		os.Getenv(SourceUrlEnvVarKey),
		"The url of the dockerfile build context")
	dockerConfigJson = flag.String("docker-config",
		os.Getenv(DockerConfigJsonEnvVarKey),
		"The Docker credential to visit the container image registry.")

	insecureRegistries = flag.String("insecure-registries",
		os.Getenv(InsecureRegistriesEnvVarKey),
		"Insecure registry using plain HTTP to push and pull. Join with ';' for multiple registries.")
	skipTlsVerifyRegistries = flag.String("skip-tls-verify-registries",
		os.Getenv(SkipTLSVerifyRegistriesEnvVarKey),
		"Insecure registry ignoring TLS verify to push and pull. Join with ';' for multiple registries.")
)

func init() {
	flag.Lookup("dockerfile").NoOptDefVal = DefaultDockerfile
	flag.Lookup("source-url").NoOptDefVal = DefaultSourceUrl
}

func main() {
	flag.Parse()
	if *dockerfilePath == "" {
		*dockerfilePath = DefaultDockerfile
	}
	if *sourceUrl == "" {
		*sourceUrl = DefaultSourceUrl
	}

	logger := logging.Default()
	if *outputImage == "" {
		logger.Error(
			fmt.Errorf("outputImage is empty"),
			fmt.Sprintf("please provide outputImage by --output-image or env variable %s", OutputImageEnvVarKey),
		)
		os.Exit(1)
	}

	if *dockerConfigJson == "" {
		logger.Info("`--docker-config` is not provided, " +
			"So you must mount Docker credential to `/kaniko/.docker/config.json` manually")
	} else {
		logger.Info("Setup Docker Config Json")
		if err := setupDockerConfigJson(*dockerConfigJson); err != nil {
			logger.Error(err, "Failed to setup docker.config.json")
			os.Exit(1)
		}
	}

	beginAt := time.Now()
	logger.Info("Downloading docker build context...")
	if err := fetchSource(logger, BuildContextDir); err != nil {
		logger.Error(err, "Failed to fetch build context")
		os.Exit(1)
	}
	logger.Info(fmt.Sprintf("* Docker build context is ready, duration: %v", time.Since(beginAt)))

	beginAt = time.Now()
	logger.Info("Start building...")
	ctx := context.Background()
	signal := make(chan int)
	cmd := buildKanikoExecutorCmd(ctx, signal)
	if err := cmd.Start(); err != nil {
		logger.Error(err, "    !! Build failed")
		os.Exit(1)
	}

	// Decompressing the image layer is time-consuming.
	// Keep printing logs to avoid being misunderstood that the program is suspended.
	go func() {
		for {
			select {
			case <-time.After(30 * time.Second):
				fmt.Print(".")
			case <-signal:

			}
		}
	}()
	if err := cmd.Wait(); err != nil {
		logger.Error(err, "    !! Build failed")
		os.Exit(1)
	}
	logger.Info(fmt.Sprintf("* Build success, duration: %v", time.Since(beginAt)))
}

// fetchSource: 拉取源码
func fetchSource(logger logr.Logger, contextDir string) error {
	url, err := url.Parse(*sourceUrl)
	if err != nil {
		return err
	}
	switch url.Scheme {
	case "file":
		if err := fs.NewFetcher(logger).Fetch(url.Path, contextDir); err != nil {
			return err
		}
	case "http", "https":
		if err := http.NewFetcher(logger).Fetch(*sourceUrl, contextDir); err != nil {
			return err
		}
	case "git":
		return errors.New("git is not implemented")
	default:
		return errors.New("no git url, http url, or registry image provided")
	}
	return nil
}

func setupDockerConfigJson(dockerConfigJson string) error {
	if err := os.MkdirAll(filepath.Dir(DockerConfigJsonPath), os.ModeDir); err != nil {
		return errors.Wrapf(err, "failed to setup %s", DockerConfigJsonPath)
	}
	content, err := base64.StdEncoding.DecodeString(dockerConfigJson)
	if err != nil {
		return errors.Wrap(err, "failed to decode DockerConfigJson from env")
	}
	if err := ioutil.WriteFile(DockerConfigJsonPath, content, 0755); err != nil {
		return errors.Wrapf(err, "failed to write %s", DockerConfigJsonPath)
	}
	return nil
}

func buildKanikoExecutorCmd(ctx context.Context, signal chan int) *exec.Cmd {
	args := []string{
		"--dockerfile", *dockerfilePath,
		"--context", fmt.Sprintf("dir://%s", BuildContextDir),
		"--destination", *outputImage,
		// Multi-stage builds fail when run in kind, the temporary solution is ignoring `/product_uuid`
		// See: https://github.com/GoogleContainerTools/kaniko/issues/2164
		"--ignore-path", "/product_uuid",
	}
	if *buildArgs != "" {
		// TODO: split buildArgs
		args = append(args, "--build-arg", *buildArgs)
	}
	if *cacheRepo != "" {
		args = append(args, "--cache", "--cache-repo", *cacheRepo)
	}
	if *insecureRegistries != "" {
		parts := strings.Split(*insecureRegistries, ",")
		for _, insecureRegistry := range parts {
			args = append(args, "--insecure-registry", insecureRegistry)
		}
	}
	if *skipTlsVerifyRegistries != "" {
		parts := strings.Split(*skipTlsVerifyRegistries, ",")
		for _, skipTlsVerifyRegistry := range parts {
			args = append(args, "--skip-tls-verify-registry", skipTlsVerifyRegistry)
		}
	}

	cmd := exec.CommandContext(ctx, "/kaniko/executor", args...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = utils.NewWriterWrapper(os.Stdout, signal)
	cmd.Stderr = utils.NewWriterWrapper(os.Stderr, signal)
	return cmd
}
