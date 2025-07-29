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
	"context"
	"io/fs"
	"os"
	"path/filepath"

	"github.com/mholt/archives"
	"github.com/samber/lo"
)

// ArchiveTGZ 将 sourceDir 目录打包成 destTGZ
func ArchiveTGZ(ctx context.Context, sourceDir, destTGZ string) error {
	entries, err := os.ReadDir(sourceDir)
	if err != nil {
		return err
	}

	files, err := archives.FilesFromDisk(ctx, nil, lo.SliceToMap(entries, func(entry fs.DirEntry) (string, string) {
		return filepath.Join(sourceDir, entry.Name()), ""
	}))
	if err != nil {
		return err
	}

	if err = os.MkdirAll(filepath.Dir(destTGZ), 0o744); err != nil {
		return err
	}

	out, err := os.Create(destTGZ)
	if err != nil {
		return err
	}
	defer out.Close()

	format := archives.CompressedArchive{
		Compression: archives.Gz{},
		Archival:    archives.Tar{},
	}

	err = format.Archive(ctx, out, files)
	if err != nil {
		return err
	}
	return nil
}
