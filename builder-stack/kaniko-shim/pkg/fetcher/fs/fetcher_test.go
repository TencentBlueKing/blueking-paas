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
	"io/ioutil"
	"log"
	"os"
	"path/filepath"

	"github.com/go-logr/stdr"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	fetcher "github.com/TencentBlueking/bkpaas/kaniko-shim/pkg/fetcher/fs"
)

var (
	basePath = "../testdata"
)

var _ = Describe("FileSystem", func() {
	var (
		destDir string
	)

	BeforeEach(func() {
		var err error
		destDir, err = ioutil.TempDir("", "fetch_test")
		Expect(err).To(BeNil())

	})
	AfterEach(func() {
		os.RemoveAll(destDir)
	})

	DescribeTable("Decompress source to destDir and read Procfile", func(source, expected string) {
		sourcePath := filepath.Join(basePath, source)
		err := fetcher.NewFetcher(stdr.New(log.Default())).Fetch(sourcePath, destDir)
		Expect(err).To(BeNil())

		content, err := ioutil.ReadFile(filepath.Join(destDir, "Procfile"))
		Expect(err).To(BeNil())
		Expect(string(content)).To(Equal(expected))
	},
		Entry("tarball", "project.tar", "hello: echo hello ${who:-world}!"),
		Entry("tarball + gzip", "project.tgz", "hello: echo hello ${who:-world}!"),
		Entry("tarball + gzip", "project.tar.gz", "hello: echo hello ${who:-world}!"),
		Entry("zip", "project.zip", "hello: echo hello ${who:-world}!"),
		// wrong ext case, only tarball and zip will work well in http fetcher
		Entry("tarball", "project.tar.unknown", "hello: echo hello ${who:-world}!"),
		Entry("zip", "project.zip.unknown", "hello: echo hello ${who:-world}!"),
	)

	DescribeTable("Detect archiver type failed", func(source, expected string) {
		sourcePath := filepath.Join(basePath, source)
		err := fetcher.NewFetcher(stdr.New(log.Default())).Fetch(sourcePath, destDir)
		Expect(err.Error()).To(Equal("unexpected file type, must be one of .rar, .zip, .tar.gz, .tar"))
	},
		Entry("tarball + gzip", "project.tgz.unknown", "hello: echo hello ${who:-world}!"),
		Entry("tarball + gzip", "project.tar.gz.unknown", "hello: echo hello ${who:-world}!"))
})
