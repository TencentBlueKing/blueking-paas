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

package appdesc

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Test app desc file", func() {
	var tmpAppDir string
	var tmpDescFilePath string

	appDescTestYaml := `spec_version: 2
module:
  language: Python
  scripts:
    pre_release_hook: "python manage.py migrate --no-input"
  processes:
    web:
      command: python manage.py runserver
    worker:
      command: celery -A app worker --loglevel=info
`

	BeforeEach(func() {
		tmpAppDir, _ = os.MkdirTemp("", "app")
		tmpDescFilePath = filepath.Join(tmpAppDir, "app_desc.yaml")
	})
	AfterEach(func() {
		Expect(os.RemoveAll(tmpAppDir)).To(BeNil())
	})

	Context("Test valid app desc file", func() {
		DescribeTable("Test ParsePreReleaseHook", func(appDescYaml, expectedHookCommand string) {
			Expect(os.WriteFile(tmpDescFilePath, []byte(appDescYaml), 0o644)).To(BeNil())

			hookCommand, err := ParsePreReleaseHook(tmpDescFilePath)
			Expect(err).To(BeNil())
			Expect(hookCommand).To(Equal(expectedHookCommand))
		}, Entry("has pre_release_hook", appDescTestYaml, "python manage.py migrate --no-input"),
			Entry("no pre_release_hook", `spec_version: 2
module:
language: Python
scripts:
test: "python"`, ""),
			Entry("no pre_release_hook", `spec_version: 2`, ""))

		It("Test TransformToProcfile", func() {
			Expect(os.WriteFile(tmpDescFilePath, []byte(appDescTestYaml), 0o644)).To(BeNil())
			procString, err := TransformToProcfile(tmpDescFilePath)
			Expect(err).To(BeNil())
			Expect(
				procString,
			).To(Equal("web: python manage.py runserver\nworker: celery -A app worker --loglevel=info"))
		})
	})
	Context("Test invalid app desc file", func() {
		It("Test ParsePreReleaseHook", func() {
			Expect(os.WriteFile(tmpDescFilePath, []byte(`abc`), 0o644)).To(BeNil())

			_, err := ParsePreReleaseHook(tmpDescFilePath)
			Expect(err).NotTo(BeNil())
		})

		It("Test TransformToProcfile", func() {
			Expect(os.WriteFile(tmpDescFilePath, []byte(`abc`), 0o644)).To(BeNil())

			_, err := TransformToProcfile(tmpDescFilePath)
			Expect(err).NotTo(BeNil())
		})
	})
})
