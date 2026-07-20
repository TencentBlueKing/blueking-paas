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

// Package main entrypoint
package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"time"

	"github.com/go-logr/logr"
	flag "github.com/spf13/pflag"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

const (
	// DefaultBuildInitPath The path of build-init cmd
	DefaultBuildInitPath = "/blueking-shim/bin/build-init"
	// DefaultLifecycleDriverPath The path of lifecycle-driver cmd
	DefaultLifecycleDriverPath = "/blueking-shim/bin/lifecycle-driver"
)

var (
	buildInit       = flag.String("build-init", DefaultBuildInitPath, "path to build-init")
	lifecycleDriver = flag.String("lifecycle-driver", DefaultLifecycleDriverPath, "path to lifecycle-driver")
	// exitDelay is set by apiserver when creating the build pod, via --exit-delay flag
	// or CNB_EXIT_DELAY env var.
	exitDelay = flag.String(
		"exit-delay",
		utils.EnvOrDefault("CNB_EXIT_DELAY", "0"),
		"sleep delay duration(string like 1m30s) before exit",
	)
)

func init() {
	flag.Lookup("build-init").NoOptDefVal = DefaultBuildInitPath
	flag.Lookup("lifecycle-driver").NoOptDefVal = DefaultLifecycleDriverPath
	flag.Lookup("exit-delay").NoOptDefVal = utils.EnvOrDefault("CNB_EXIT_DELAY", "0")
}

func main() {
	flag.Parse()
	logger := logging.Default()

	// Run the build, returns exit code
	code := run(logger)

	// Build debug: write markers and keep container alive before exit
	if duration, err := getExitDelay(); err != nil {
		logger.Error(err, "Invalid exit-delay, keep-alive disabled")
	} else if duration > 0 {
		writeMarkers(logger, code)
		preExit(logger, duration)
	}
	os.Exit(code)
}

// run executes the full build pipeline and returns an exit code.
func run(logger logr.Logger) int {
	ctx := context.Background()
	if err := makeBuildInitCmd(ctx).Run(); err != nil {
		logger.Error(err, "!! Setup Build Environ Failed")
		return 1
	}
	if err := makeLifecycleDriverCmd(ctx).Run(); err != nil {
		logger.Error(err, "!! Build failed")
		return 1
	}
	return 0
}

// getExitDelay parses CNB_EXIT_DELAY and returns the sleep duration and any
// parse error. Returns 0 when the flag is unset.
func getExitDelay() (time.Duration, error) {
	duration, err := time.ParseDuration(*exitDelay)
	if err != nil {
		return 0, err
	}
	return duration, nil
}

// writeMarkers writes the build-done marker and result markers based on exit code.
func writeMarkers(logger logr.Logger, code int) {
	if code == 0 {
		if err := utils.WriteBuildResultSuccess(); err != nil {
			logger.Error(err, "failed to write build-result-success marker")
		}
	} else {
		if err := utils.WriteBuildResultFailed(); err != nil {
			logger.Error(err, "failed to write build-result-failed marker")
		}
	}
	if err := utils.WriteBuildDone(); err != nil {
		logger.Error(err, "failed to write build-done marker")
	}
}

func makeBuildInitCmd(ctx context.Context) *exec.Cmd {
	cmd := exec.CommandContext(ctx, *buildInit)
	cmd.Env = os.Environ()
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd
}

func makeLifecycleDriverCmd(ctx context.Context) *exec.Cmd {
	cmd := exec.CommandContext(ctx, *lifecycleDriver)
	cmd.Env = os.Environ()
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd
}

// preExit logs and sleeps for the given duration before exit.
func preExit(logger logr.Logger, duration time.Duration) {
	logger.Info(fmt.Sprintf("Sleeping %v before exit", duration))
	time.Sleep(duration)
}
