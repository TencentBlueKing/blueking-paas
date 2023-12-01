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
package fs

import (
	"fmt"
	"os"

	"github.com/go-logr/logr"
	"github.com/mholt/archiver/v3"
	"github.com/pkg/errors"
)

var unexpectedBlobTypeError = errors.New("unexpected file type, must be one of .rar, .zip, .tar.gz, .tar")

// Fetcher ...
type Fetcher struct {
	Logger logr.Logger
}

// NewFetcher ...
func NewFetcher(log logr.Logger) *Fetcher {
	return &Fetcher{log}
}

// Fetch src from local filesystem and extract it to destDir
func (f *Fetcher) Fetch(src string, destDir string) error {
	file, err := os.Open(src)
	if err != nil {
		return errors.Wrapf(err, "Failed to open file %s", src)
	}

	var arc archiver.Unarchiver
	if iarc, err := archiver.ByExtension(src); err == nil {
		arc = iarc.(archiver.Unarchiver)
	} else {
		arc, _ = archiver.ByHeader(file)
	}
	if arc == nil {
		return unexpectedBlobTypeError
	}
	err = arc.Unarchive(file.Name(), destDir)
	if err != nil {
		return errors.Wrapf(err, "Failed to decompress file %s", src)
	}

	f.Logger.Info(fmt.Sprintf("Successfully decompress file %s to path %q", src, destDir))
	return nil
}
