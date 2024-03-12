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
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Test os utils", func() {
	Describe("Test file zip and copy", func() {
		srcFilePath := filepath.Join("testdata", "django-helloworld.zip")

		var destAppPath, tmpPath string

		BeforeEach(func() {
			destAppPath, _ = os.MkdirTemp("", "django-helloworld")
			tmpPath, _ = os.MkdirTemp("", "tmp")
		})
		AfterEach(func() {
			Expect(os.RemoveAll(destAppPath)).To(BeNil())
			Expect(os.RemoveAll(tmpPath)).To(BeNil())
		})

		It("Test unzip file and copy dir", func() {
			Expect(Unzip(srcFilePath, tmpPath)).To(BeNil())

			Expect(CopyDir(filepath.Join(tmpPath, "django-helloworld"), destAppPath)).To(BeNil())

			_, err := os.Stat(filepath.Join(destAppPath, "helloworld", "settings.py"))
			Expect(err).To(BeNil())

			_, err = os.Stat(filepath.Join(destAppPath, "manage.py"))
			Expect(err).To(BeNil())
		})
	})
	Describe("Test SortedCompareFile", func() {
		var tmpPath string

		BeforeEach(func() {
			tmpPath, _ = os.MkdirTemp("", "dependency-files")
		})
		AfterEach(func() {
			Expect(os.RemoveAll(tmpPath)).To(BeNil())
		})

		Context("When file exist", func() {
			DescribeTable(
				"compare file",
				func(content1, content2 string, expectedEq bool) {
					filePath1 := filepath.Join(tmpPath, "file1")
					filePath2 := filepath.Join(tmpPath, "file2")
					Expect(os.WriteFile(filePath1, []byte(content1), 0o644)).To(BeNil())
					Expect(os.WriteFile(filePath2, []byte(content2), 0o644)).To(BeNil())

					eq, err := SortedCompareFile(filePath1, filePath2)
					Expect(err).To(BeNil())
					Expect(eq).To(Equal(expectedEq))
				},
				Entry("the same content but disorder", `asyncclick~=8.1.3.4
httpx~=0.25.1
django-downloadview~=2.3.0
bkstorages~=1.1.0

# PaaS 增强服务需要的依赖包，请不要修改，否则可能导致增强服务不可用
# for sentry
raven==6.10.0
`, `# PaaS 增强服务需要的依赖包，请不要修改，否则可能导致增强服务不可用
# for sentry
raven==6.10.0


asyncclick~=8.1.3.4
httpx~=0.25.1
django-downloadview~=2.3.0
bkstorages~=1.1.0
`, true),
				Entry("not the same content", "asyncclick~=8.1.3.4", "asyncclick~=9.1.3.4", false),
			)
		})
		Context("When some file not exist", func() {
			filePath1 := filepath.Join(tmpPath, "file1")
			filePath2 := filepath.Join(tmpPath, "file2")
			_, err := SortedCompareFile(filePath1, filePath2)
			Expect(err).NotTo(BeNil())
		})
	})
})
