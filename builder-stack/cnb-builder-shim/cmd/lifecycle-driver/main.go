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
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/go-logr/logr"
	flag "github.com/spf13/pflag"

	"bk.tencent.com/cnb-builder-shim/pkg/logging"
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

	// CacheImageEnvVarKey The env var key that store cache image
	CacheImageEnvVarKey = "CACHE_IMAGE"
	// OutputImageEnvVarKey The env var key that store output image
	OutputImageEnvVarKey = "OUTPUT_IMAGE"

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
	outputImage = flag.String("output-image", os.Getenv(OutputImageEnvVarKey), "The name of image that will get created by the lifecycle.")

	logLevel = flag.String("log-level", "info", "logging level")
)

func init() {
	flag.Lookup("lifecycle").NoOptDefVal = DefaultLifecycleDir
	flag.Lookup("app").NoOptDefVal = DefaultAppDir
	flag.Lookup("order").NoOptDefVal = DefaultOrderPath
	flag.Lookup("analyzed").NoOptDefVal = DefaultAnalyzedPath
	flag.Lookup("group").NoOptDefVal = DefaultGroupPath
	flag.Lookup("plan").NoOptDefVal = DefaultPlanPath
	flag.Lookup("layers").NoOptDefVal = DefaultLayersDir
	flag.Lookup("log-level").NoOptDefVal = "info"
	flag.Lookup("uid").NoOptDefVal = fmt.Sprintf("%d", DefaultUid)
	flag.Lookup("gid").NoOptDefVal = fmt.Sprintf("%d", DefaultGid)
}

// Step describe CNB Build Step
type Step struct {
	Name         string
	EnterMessage string
	Cmd          *exec.Cmd
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
	// Starting from Platform API 0.7, the analyze phase runs before the detect phase.
	steps := []Step{
		{
			"Analyze",
			"Analyzing optimization plan...",
			makeAnalyzerCmd(ctx, *lifecycleDir, *outputImage, *analyzedPath, *cacheImage, *layersDir, *logLevel, *uid, *gid),
		},
		{
			"Detect",
			"Detecting Buildpacks...",
			makeDetectorCmd(ctx, *lifecycleDir, *appDir, *orderPath, *groupPath, *planPath, *layersDir, *logLevel),
		},
	}
	if *cacheImage != "" {
		steps = append(steps, Step{
			"Restore",
			"Restoring layers from the cache...",
			makeRestorerCmd(ctx, *lifecycleDir, *cacheImage, *groupPath, *layersDir, *logLevel, *uid, *gid),
		})
	}
	steps = append(steps, Step{
		"Build",
		"Building application...",
		makeBuilderCmd(ctx, *lifecycleDir, *appDir, *groupPath, *planPath, *layersDir, *logLevel),
	}, Step{
		"Export",
		"Exporting image...",
		makeExporterCmd(ctx, *lifecycleDir, *outputImage, *appDir, *analyzedPath, *cacheImage, *groupPath, *layersDir, *logLevel, *uid, *gid),
	})

	lifecycleEnv := makeEnv(logger)
	logger.Info("==================================================")
	logger.Info("Starting builder...")
	beginAt := time.Now()
	for _, step := range steps {
		beginAt := time.Now()
		logger.Info(fmt.Sprintf("--> %s", step.EnterMessage))
		// Redirect input and output
		step.Cmd.Stdin = os.Stdin
		step.Cmd.Stderr = os.Stderr
		step.Cmd.Stdout = os.Stdout
		// setup env var
		step.Cmd.Env = lifecycleEnv
		// set user and group
		step.Cmd.SysProcAttr = makeSysProcAttr(*uid, *gid)
		err = step.Cmd.Run()
		if err != nil {
			logger.Error(err, fmt.Sprintf("!! Step %s failed", step.Name))
			os.Exit(1)
		}
		logger.Info(fmt.Sprintf("Step %s done, duration %s", step.Name, time.Since(beginAt)))
	}
	logger.Info("==================================================")
	logger.Info(fmt.Sprintf("Build success, duration: %v", time.Since(beginAt)))
}

// build the detector cmd
// detector will generate group.toml(to groupPath) and plan.toml(to planPath) based on order.toml(in orderPath) and source code(in appDir)
func makeDetectorCmd(ctx context.Context, lifecycleDir, appDir, orderPath, groupPath, planPath, layersDir, logLevel string) *exec.Cmd {
	args := []string{
		"-app", appDir,
		"-order", orderPath,
		"-group", groupPath,
		"-plan", planPath,
		"-layers", layersDir,
		"-log-level", logLevel,
	}
	cmd := exec.CommandContext(ctx, filepath.Join(lifecycleDir, "detector"), args...)
	return cmd
}

// build the analyzer cmd
// analyzer will generate analyzed.toml(to analyzedPath) based on cacheImage
func makeAnalyzerCmd(ctx context.Context, lifecycleDir, outputImage, analyzedPath, cacheImage, layersDir, logLevel string, uid, gid uint32) *exec.Cmd {
	args := []string{
		"-analyzed", analyzedPath,
		"-layers", layersDir,
		"-log-level", logLevel,
		"-uid", fmt.Sprintf("%d", uid),
		"-gid", fmt.Sprintf("%d", gid),
	}
	// analyze with cache when cacheImage is set
	if cacheImage != "" {
		args = append(args, "-cache-image", cacheImage)
	}
	args = append(args, outputImage)
	cmd := exec.CommandContext(ctx, filepath.Join(lifecycleDir, "analyzer"), args...)
	return cmd
}

// build the restorer cmd
// restorer will restore last build cache based on cacheImage and group.toml(in groupPath)
func makeRestorerCmd(ctx context.Context, lifecycleDir, cacheImage, groupPath, layersDir, logLevel string, uid, gid uint32) *exec.Cmd {
	args := []string{
		"-cache-image", cacheImage,
		"-group", groupPath,
		"-layers", layersDir,
		"-log-level", logLevel,
		"-uid", fmt.Sprintf("%d", uid),
		"-gid", fmt.Sprintf("%d", gid),
	}
	cmd := exec.CommandContext(ctx, filepath.Join(lifecycleDir, "restorer"), args...)
	return cmd
}

// build the builder cmd
// builder will build the app(in appDir) based on group.toml(in groupPath) and plan.toml(in planPath)
func makeBuilderCmd(ctx context.Context, lifecycleDir, appDir, groupPath, planPath, layersDir, logLevel string) *exec.Cmd {
	args := []string{
		"-app", appDir,
		"-group", groupPath,
		"-plan", planPath,
		"-layers", layersDir,
		"-log-level", logLevel,
	}
	cmd := exec.CommandContext(ctx, filepath.Join(lifecycleDir, "builder"), args...)
	return cmd
}

// build the exporter cmd
// exporter will push the app image and cache image to container image registry
func makeExporterCmd(ctx context.Context, lifecycleDir, outputImage, appDir, analyzedPath, cacheImage, groupPath, layersDir, logLevel string, uid, gid uint32) *exec.Cmd {
	args := []string{
		"-app", appDir,
		"-analyzed", analyzedPath,
		"-group", groupPath,
		"-layers", layersDir,
		"-log-level", logLevel,
		"-uid", fmt.Sprintf("%d", uid),
		"-gid", fmt.Sprintf("%d", gid),
	}
	// export cache when cacheImage is set
	if cacheImage != "" {
		args = append(args, "-cache-image", cacheImage)
	}
	args = append(args, outputImage)
	cmd := exec.CommandContext(ctx, filepath.Join(lifecycleDir, "exporter"), args...)
	return cmd
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

func makeSysProcAttr(uid, gid uint32) *syscall.SysProcAttr {
	sysProcAttr := syscall.SysProcAttr{}
	sysProcAttr.Credential = &syscall.Credential{
		Uid:         uid,
		Gid:         gid,
		Groups:      nil,
		NoSetGroups: false,
	}
	return &sysProcAttr
}
