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

package utils

import (
	"os"
)

// Marker files are written to /tmp inside the build container to indicate the
// build completion status. When the container is kept alive (via CNB_EXIT_DELAY /
// --exit-delay), the platform queries these files through exec probes to determine
// the build result:
//
//   Startup Probe:  test -f /tmp/build-done              -> containerStatus.started
//   Readiness Probe: test -f /tmp/build-result-success   -> containerStatus.ready
//
// Build result is determined by started + ready. The failed marker is not
// consumed by any probe; it exists only for operator visibility during debugging.
//
// - /tmp/build-done:              written once the build pipeline finishes (regardless of result).
// - /tmp/build-result-success:    written only when the build succeeded.
// - /tmp/build-result-failed:     written only when the build failed (NOT used by probes).

const (
	// BuildDoneMarker is the marker file indicating the build has completed (whether success or failure).
	BuildDoneMarker = "/tmp/build-done"
	// BuildResultSuccessMarker is the marker file indicating the build succeeded.
	BuildResultSuccessMarker = "/tmp/build-result-success"
	// BuildResultFailedMarker is the marker file indicating the build failed (for debugging purposes).
	BuildResultFailedMarker = "/tmp/build-result-failed"
)

// WriteBuildDone writes the build-done marker file.
func WriteBuildDone() error {
	return os.WriteFile(BuildDoneMarker, []byte("done"), 0o644)
}

// WriteBuildResultSuccess writes the build-result-success marker file.
func WriteBuildResultSuccess() error {
	return os.WriteFile(BuildResultSuccessMarker, []byte("success"), 0o644)
}

// WriteBuildResultFailed writes the build-result-failed marker file.
func WriteBuildResultFailed() error {
	return os.WriteFile(BuildResultFailedMarker, []byte("failed"), 0o644)
}
