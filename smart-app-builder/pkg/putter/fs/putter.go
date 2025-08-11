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
	"net/url"
	"os"
	"path/filepath"

	"github.com/go-logr/logr"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// Putter ...
type Putter struct {
	Logger logr.Logger
}

// NewPutter ...
func NewPutter(log logr.Logger) *Putter {
	return &Putter{log}
}

// Put src from local filesystem to destDir
func (p *Putter) Put(src string, destUrl *url.URL) error {
	filePath := destUrl.Path
	fileName := filepath.Base(filePath)
	if filepath.Ext(fileName) == ".tgz" {
		if err := os.MkdirAll(filepath.Dir(filePath), 0o744); err != nil {
			return err
		}
		return utils.CopyFile(src, filePath)
	}

	// Assume dest is a directory, otherwise an error occurs.
	if err := os.MkdirAll(filePath, 0o744); err != nil {
		return err
	}
	return utils.CopyFile(src, filepath.Join(filePath, filepath.Base(src)))
}
