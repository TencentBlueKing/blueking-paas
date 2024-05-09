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
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/go-logr/logr"
	flag "github.com/spf13/pflag"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/lifecycle/phase"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

const (
	// DefaultLifecycleDir is the default lifecycle dir
	DefaultLifecycleDir = "/lifecycle"
	// DefaultAppDir is the default build dir
	DefaultAppDir = "/app"
	// DefaultOrderPath is the default path to store order.toml
	DefaultOrderPath = "/cnb/order.toml"
	// DefaultLayersDir is the default dir to store bp layers
	DefaultLayersDir = "/layers"
	// DefaultLogLevel is the default log level for lifecycle
	DefaultLogLevel = "info"

	// CacheImageEnvVarKey The env var key that store cache image
	CacheImageEnvVarKey = "CACHE_IMAGE"
	// OutputImageEnvVarKey The env var key that store output image
	OutputImageEnvVarKey = "OUTPUT_IMAGE"
	// UseDockerDaemonEnvVarKey The env var key that store a flag meaning if use docker daemon
	UseDockerDaemonEnvVarKey = "USE_DOCKER_DAEMON"
	// LogLevelEnvVarKey The env var key that store log level
	LogLevelEnvVarKey = "CNB_LOG_LEVEL"

	// DevModeEnvVarKey The env var key that indicates whether to use the dev mode or not
	DevModeEnvVarKey = "DEV_MODE"

	// DefaultUid is the default uid to run lifecycle
	DefaultUid uint32 = 2000
	// DefaultGid is the default gid to run lifecycle
	DefaultGid uint32 = 2000
)

var (
	// DefaultGroupPath is the default dir to store group.toml
	DefaultGroupPath = filepath.Join(DefaultLayersDir, "group.toml")
	// DefaultAnalyzedPath is the default dir to store analyzed.toml
	DefaultAnalyzedPath = filepath.Join(DefaultLayersDir, "analyzed.toml")
	// DefaultPlanPath is the default dir to store plan.toml
	DefaultPlanPath = filepath.Join(DefaultLayersDir, "plan.toml")

	lifecycleDir = flag.String("lifecycle", DefaultLifecycleDir, "path to lifecycle binary directory.")
	appDir       = flag.String("app", DefaultAppDir, "path to app directory.")
	orderPath    = flag.String("order", DefaultOrderPath, "path to order.toml.")
	analyzedPath = flag.String("analyzed", DefaultAnalyzedPath, "path to analyzed.toml")
	groupPath    = flag.String("group", DefaultGroupPath, "path to group.toml")
	planPath     = flag.String("plan", DefaultPlanPath, "path to plan.toml")
	layersDir    = flag.String("layers", DefaultLayersDir, "path to layers directory")

	uid = flag.Uint32("uid", DefaultUid, "UID of user's group in the stack's build and run images")
	gid = flag.Uint32("gid", DefaultGid, "GID of user's group in the stack's build and run images")

	cacheImage  = flag.String("cache-image", os.Getenv(CacheImageEnvVarKey), "cache image tag name")
	outputImage = flag.String(
		"output-image",
		os.Getenv(OutputImageEnvVarKey),
		"The name of image that will get created by the lifecycle.",
	)
	useDaemon = flag.Bool("daemon", utils.BoolEnv(UseDockerDaemonEnvVarKey), "export image to docker daemon")
	logLevel  = flag.String("log-level", utils.EnvOrDefault(LogLevelEnvVarKey, DefaultLogLevel), "logging level")

	dev = flag.Bool("dev", utils.BoolEnv(DevModeEnvVarKey), "use dev mode or not")
)

func init() {
	flag.Lookup("lifecycle").NoOptDefVal = DefaultLifecycleDir
	flag.Lookup("app").NoOptDefVal = DefaultAppDir
	flag.Lookup("order").NoOptDefVal = DefaultOrderPath
	flag.Lookup("analyzed").NoOptDefVal = DefaultAnalyzedPath
	flag.Lookup("group").NoOptDefVal = DefaultGroupPath
	flag.Lookup("plan").NoOptDefVal = DefaultPlanPath
	flag.Lookup("layers").NoOptDefVal = DefaultLayersDir
	flag.Lookup("log-level").NoOptDefVal = DefaultLogLevel
	flag.Lookup("uid").NoOptDefVal = fmt.Sprintf("%d", DefaultUid)
	flag.Lookup("gid").NoOptDefVal = fmt.Sprintf("%d", DefaultGid)
}

func main() {
	flag.Parse()
	logger := logging.Default()

	stat, err := os.Stat(*lifecycleDir)
	if os.IsNotExist(err) {
		logger.Error(err, fmt.Sprintf("%s is not exist", *lifecycleDir))
		os.Exit(1)
	}
	if !stat.IsDir() {
		logger.Info(fmt.Sprintf("%s is not a dir", *lifecycleDir))
		os.Exit(1)
	}

	ctx := context.Background()
	runLifecycle(ctx, logger, *dev)
}

// make envs for lifecycle command
// only those envs with "CNB_" prefix will be provided to lifecycle command
func makeEnv(logger logr.Logger) (env []string) {
	allEnv := os.Environ()
	for _, e := range allEnv {
		pair := strings.SplitN(e, "=", 2)
		key, _ := pair[0], pair[1]
		if strings.HasPrefix(key, "CNB_") {
			env = append(env, e)
		} else {
			logger.V(2).Info(fmt.Sprintf("skip env var %s", key))
		}
	}
	return
}

func runLifecycle(ctx context.Context, logger logr.Logger, dev bool) {
	logger.Info("==================================================")
	logger.Info("Starting builder...")

	beginAt := time.Now()

	var steps []phase.Step
	if dev {
		steps = getDevSteps(ctx)
	} else {
		steps = getBuilderSteps(ctx)
	}

	executeSteps(logger, steps)

	logger.Info("==================================================")
	logger.Info(fmt.Sprintf("Build success, duration: %v", time.Since(beginAt)))
}

func executeSteps(logger logr.Logger, steps []phase.Step) {
	lifecycleEnv := makeEnv(logger)

	for _, step := range steps {
		beginAt := time.Now()
		logger.Info(fmt.Sprintf("--> %s", step.EnterMessage))
		if err := step.WithCmdOptions(phase.WithEnv(lifecycleEnv)).Execute(); err != nil {
			logger.Error(err, fmt.Sprintf("!! Step %s failed", step.Name))
			os.Exit(1)
		}
		logger.Info(fmt.Sprintf("Step %s done, duration %s", step.Name, time.Since(beginAt)))
	}
}

func getBuilderSteps(ctx context.Context) []phase.Step {
	// Starting from Platform API 0.7, the analyze phase runs before the detect phase.
	steps := []phase.Step{
		phase.MakeAnalyzerStep(
			ctx,
			*lifecycleDir,
			*outputImage,
			*analyzedPath,
			*cacheImage,
			*layersDir,
			*logLevel,
			*useDaemon,
			*uid,
			*gid,
		),
		phase.MakeDetectorStep(
			ctx,
			*lifecycleDir,
			*appDir,
			*orderPath,
			*groupPath,
			*planPath,
			*layersDir,
			*logLevel,
			*uid,
			*gid,
		),
	}
	if *cacheImage != "" {
		steps = append(steps, phase.MakeRestorerStep(ctx, *lifecycleDir, *cacheImage, *groupPath, *layersDir,
			*logLevel, *useDaemon, *uid, *gid))
	}
	steps = append(steps,
		phase.MakeBuilderStep(ctx, *lifecycleDir, *appDir, *groupPath, *planPath, *layersDir,
			*logLevel, *uid, *gid),
		phase.MakeExporterStep(
			ctx,
			*lifecycleDir,
			*outputImage,
			*appDir,
			*analyzedPath,
			*cacheImage,
			*groupPath,
			*layersDir,
			*logLevel,
			*useDaemon,
			*uid,
			*gid,
		))
	return steps
}

func getDevSteps(ctx context.Context) []phase.Step {
	return []phase.Step{
		phase.MakeDetectorStep(
			ctx,
			*lifecycleDir,
			*appDir,
			*orderPath,
			*groupPath,
			*planPath,
			*layersDir,
			*logLevel,
			*uid,
			*gid,
		),
		phase.MakeBuilderStep(ctx, *lifecycleDir, *appDir, *groupPath, *planPath, *layersDir,
			*logLevel, *uid, *gid),
	}
}
