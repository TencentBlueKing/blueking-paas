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
	"os"
	"os/exec"

	flag "github.com/spf13/pflag"

	"bk.tencent.com/cnb-builder-shim/pkg/logging"
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
)

func init() {
	flag.Lookup("build-init").NoOptDefVal = DefaultBuildInitPath
	flag.Lookup("lifecycle-driver").NoOptDefVal = DefaultLifecycleDriverPath
}

func main() {
	flag.Parse()
	logger := logging.Default()

	ctx := context.Background()
	if err := makeBuildInitCmd(ctx).Run(); err != nil {
		logger.Error(err, "!! Setup Build Environ Failed")
		os.Exit(1)
	}
	if err := makeLifecycleDriverCmd(ctx).Run(); err != nil {
		logger.Error(err, "!! Build failed")
		os.Exit(1)
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
