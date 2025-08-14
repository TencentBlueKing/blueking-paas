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

package uploader_test

import (
	"net/url"
	"os"
	"path/filepath"

	"github.com/go-logr/logr"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/uploader"
)

var _ = Describe("FileSystem", func() {
	var destDir string
	var basePath = "./testdata"

	BeforeEach(func() {
		var err error
		destDir, err = os.MkdirTemp("", "put_test")
		Expect(err).To(BeNil())

	})
	AfterEach(func() {
		os.RemoveAll(destDir)
	})

	Context("put tgz file to file path", func() {
		It("should copy content correctly", func() {
			srcPath := filepath.Join(basePath, "project.tgz")
			destPath := filepath.Join(destDir, "artifact.tgz")
			u := &url.URL{Scheme: "file", Path: destPath}

			err := uploader.NewFsUploader(logr.Discard()).Upload(srcPath, u)
			Expect(err).To(BeNil())

			srcContent, err := os.ReadFile(srcPath)
			Expect(err).To(BeNil())
			destContent, err := os.ReadFile(destPath)
			Expect(err).To(BeNil())
			Expect(destContent).To(Equal(srcContent))
		})
	})

	Context("put tgz file to directory", func() {
		It("should copy content correctly", func() {
			srcPath := filepath.Join(basePath, "project.tgz")
			u := &url.URL{Scheme: "file", Path: destDir}

			err := uploader.NewFsUploader(logr.Discard()).Upload(srcPath, u)
			Expect(err).To(BeNil())

			srcContent, err := os.ReadFile(srcPath)
			Expect(err).To(BeNil())
			dstFile := filepath.Join(destDir, filepath.Base(srcPath))
			destContent, err := os.ReadFile(dstFile)
			Expect(err).To(BeNil())
			Expect(destContent).To(Equal(srcContent))
		})
	})
})
