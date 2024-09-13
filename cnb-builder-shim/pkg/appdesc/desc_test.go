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
  env_variables:
    - key: FOO
      value: value_of_foo
      description: description_of_foo
    - key: BAR
      value: value_of_bar
      description: description_of_bar
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
		DescribeTable("Test parse PreReleaseHook", func(appDescYaml, expectedHookCommand string) {
			Expect(os.WriteFile(tmpDescFilePath, []byte(appDescYaml), 0o644)).To(BeNil())

			appDesc, err := UnmarshalToAppDesc(tmpDescFilePath)
			Expect(err).To(BeNil())
			Expect(appDesc.Module.Scripts.PreReleaseHook).To(Equal(expectedHookCommand))
		}, Entry("has pre_release_hook", appDescTestYaml, "python manage.py migrate --no-input"),
			Entry("no pre_release_hook", `spec_version: 2
module:
language: Python
scripts:
test: "python"`, ""),
			Entry("no pre_release_hook", `spec_version: 2`, ""))

		DescribeTable("Test parse env_variables", func(appDescYaml string, expectedEnvs []Env) {
			Expect(os.WriteFile(tmpDescFilePath, []byte(appDescYaml), 0o644)).To(BeNil())

			appDesc, err := UnmarshalToAppDesc(tmpDescFilePath)
			Expect(err).To(BeNil())
			Expect(appDesc.Module.ProcEnvs).To(Equal(expectedEnvs))
		}, Entry("has env_variables", appDescTestYaml, []Env{
			{Key: "FOO", Value: "value_of_foo"}, {Key: "BAR", Value: "value_of_bar"},
		}), Entry("no env_variables", `spec_version: 2`, nil))

		It("Test TransformToProcfile", func() {
			Expect(os.WriteFile(tmpDescFilePath, []byte(appDescTestYaml), 0o644)).To(BeNil())
			procString, err := TransformToProcfile(tmpDescFilePath)
			Expect(err).To(BeNil())
			Expect(procString).To(ContainSubstring("worker: celery -A app worker --loglevel=info"))
			Expect(procString).To(ContainSubstring("web: python manage.py runserver"))
		})
	})
	Context("Test invalid app desc file", func() {
		It("Test unmarshal to app desc", func() {
			Expect(os.WriteFile(tmpDescFilePath, []byte(`abc`), 0o644)).To(BeNil())

			_, err := UnmarshalToAppDesc(tmpDescFilePath)
			Expect(err).NotTo(BeNil())
		})

		It("Test TransformToProcfile", func() {
			Expect(os.WriteFile(tmpDescFilePath, []byte(`abc`), 0o644)).To(BeNil())

			_, err := TransformToProcfile(tmpDescFilePath)
			Expect(err).NotTo(BeNil())
		})
	})
})
