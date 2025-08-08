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
package fs_test

import (
	"net/url"
	"os"
	"path/filepath"

	"github.com/go-logr/logr"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	putFs "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/putter/fs"
)

var basePath = "../testdata"

var _ = Describe("FileSystem", func() {
	var destDir string

	BeforeEach(func() {
		var err error
		destDir, err = os.MkdirTemp("", "put_test")
		Expect(err).To(BeNil())

	})
	AfterEach(func() {
		os.RemoveAll(destDir)
	})

	DescribeTable("Put smart file to destDir",
		func(srcFileName string, isDestFile bool) {
			srcPath := filepath.Join(basePath, srcFileName)
			destPath := filepath.Join(destDir, "artifact.tgz")
			if !isDestFile {
				destPath = destDir
			}
			u := &url.URL{Scheme: "file", Path: destPath}

			err := putFs.NewPutter(logr.Discard()).Put(srcPath, u)
			Expect(err).To(BeNil())

			if isDestFile {
				srcContent, err := os.ReadFile(srcPath)
				Expect(err).To(BeNil())

				destContent, err := os.ReadFile(destPath)
				Expect(err).To(BeNil())

				Expect(destContent).To(Equal(srcContent))
			} else {
				srcContent, err := os.ReadFile(srcPath)
				Expect(err).To(BeNil())

				dstFile := filepath.Join(destPath, filepath.Base(srcPath))
				destContent, err := os.ReadFile(dstFile)
				Expect(err).To(BeNil())

				Expect(destContent).To(Equal(srcContent))
			}
		},
		Entry("put valid tgz file to .tgz", "project.tgz", true),
		Entry("put valid tgz file to .tgz in dir", "project.tgz", false),
	)
})
