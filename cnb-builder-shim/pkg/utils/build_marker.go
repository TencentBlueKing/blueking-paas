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

	"github.com/go-logr/logr"
)

const (
	// BuildDoneMarker is the marker file indicating the build has completed (whether success or failure).
	BuildDoneMarker = "/tmp/build-done"
	// BuildResultSuccessMarker is the marker file indicating the build succeeded.
	BuildResultSuccessMarker = "/tmp/build-result-success"
	// BuildResultFailedMarker is the marker file indicating the build failed (for debugging purposes).
	BuildResultFailedMarker = "/tmp/build-result-failed"
)

// WriteBuildDone writes the build-done marker file.
func WriteBuildDone(logger logr.Logger) {
	if err := os.WriteFile(BuildDoneMarker, []byte("done"), 0o644); err != nil {
		logger.Error(err, "failed to write build-done marker")
	}
}

// WriteBuildResultSuccess writes the build-result-success marker file.
func WriteBuildResultSuccess(logger logr.Logger) {
	if err := os.WriteFile(BuildResultSuccessMarker, []byte("success"), 0o644); err != nil {
		logger.Error(err, "failed to write build-result-success marker")
	}
}

// WriteBuildResultFailed writes the build-result-failed marker file.
func WriteBuildResultFailed(logger logr.Logger) {
	if err := os.WriteFile(BuildResultFailedMarker, []byte("failed"), 0o644); err != nil {
		logger.Error(err, "failed to write build-result-failed marker")
	}
}
