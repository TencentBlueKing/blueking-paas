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

package phase

import (
	"context"
	"fmt"
	"os/exec"
	"path/filepath"
)

// MakeAnalyzerStep build the analyzer step
// analyzer will generate analyzed.toml(to analyzedPath) based on cacheImage
func MakeAnalyzerStep(
	ctx context.Context,
	lifecycleDir, outputImage, analyzedPath, cacheImage, layersDir, logLevel string,
	useDaemon bool,
	uid, gid uint32,
) Step {
	var opts []CmdOptsProvider
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
	if useDaemon {
		args = append(args, "-daemon")
		opts = append(opts, WithRoot())
	} else {
		opts = append(opts, WithUser(uid, gid))
	}
	args = append(args, outputImage)
	cmd := exec.CommandContext(ctx, filepath.Join(lifecycleDir, "analyzer"), args...)
	return makeStep("Analyze", "Analyzing optimization plan...", cmd, opts...)

}
