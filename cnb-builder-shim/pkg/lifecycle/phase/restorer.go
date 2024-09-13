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

// MakeRestorerStep build the restorer step
// restorer will restore last build cache based on cacheImage and group.toml(in groupPath)
func MakeRestorerStep(
	ctx context.Context,
	lifecycleDir, cacheImage, groupPath, layersDir, logLevel string,
	useDaemon bool,
	uid, gid uint32,
) Step {
	var opts []CmdOptsProvider
	args := []string{
		"-cache-image", cacheImage,
		"-group", groupPath,
		"-layers", layersDir,
		"-log-level", logLevel,
		"-uid", fmt.Sprintf("%d", uid),
		"-gid", fmt.Sprintf("%d", gid),
	}
	if useDaemon {
		args = append(args, "-daemon")
		opts = append(opts, WithRoot())
	} else {
		opts = append(opts, WithUser(uid, gid))
	}
	cmd := exec.CommandContext(ctx, filepath.Join(lifecycleDir, "restorer"), args...)
	return makeStep("Restore", "Restoring layers from the cache...", cmd, opts...)
}
