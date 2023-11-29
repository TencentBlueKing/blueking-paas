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
package http_test

import (
	"fmt"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	fetcher "bk.tencent.com/cnb-builder-shim/pkg/fetcher/http"
	"bk.tencent.com/cnb-builder-shim/pkg/logging"
)

var (
	server  *httptest.Server
	handler http.Handler
)

var _ = BeforeSuite(func() {
	handler = http.FileServer(http.Dir("../testdata"))
	server = httptest.NewServer(handler)
})
var _ = AfterSuite(func() {
	server.Close()
})

var _ = Describe("Http", func() {
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

	DescribeTable("Download source from server, decompress it to destDir and read Procfile", func(source, expected string) {
		sourceUrl := fmt.Sprintf("%s/%s", server.URL, source)
		err := fetcher.NewFetcher(logging.Default()).Fetch(sourceUrl, destDir)
		Expect(err).To(BeNil())

		content, err := ioutil.ReadFile(filepath.Join(destDir, "Procfile"))
		Expect(err).To(BeNil())
		Expect(string(content)).To(Equal(expected))
	},
		Entry("tarball", "project.tar", "hello: echo hello ${who:-world}!"),
		Entry("tarball + gzip", "project.tgz", "hello: echo hello ${who:-world}!"),
		Entry("tarball + gzip", "project.tar.gz", "hello: echo hello ${who:-world}!"),
		Entry("zip", "project.zip", "hello: echo hello ${who:-world}!"),
		// wrong ext case, will work well in http fetcher
		Entry("tarball", "project.tar.unknown", "hello: echo hello ${who:-world}!"),
		Entry("tarball + gzip", "project.tgz.unknown", "hello: echo hello ${who:-world}!"),
		Entry("tarball + gzip", "project.tar.gz.unknown", "hello: echo hello ${who:-world}!"),
		Entry("zip", "project.zip.unknown", "hello: echo hello ${who:-world}!"),
	)
})
