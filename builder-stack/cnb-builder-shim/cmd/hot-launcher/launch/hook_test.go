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

package launch

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Test hook", func() {

	oldAppDir := DefaultAppDir

	BeforeEach(func() {
		DefaultAppDir, _ = os.MkdirTemp("", "app")

	})
	AfterEach(func() {
		Expect(os.RemoveAll(DefaultAppDir)).To(BeNil())
		DefaultAppDir = oldAppDir
	})

	DescribeTable("Test parsePreReleaseHook", func(appDescYaml, expectedHookCommand string) {
		Expect(os.WriteFile(filepath.Join(DefaultAppDir, "app_desc.yaml"), []byte(appDescYaml), 0644)).To(BeNil())
		hookCommand, err := parsePreReleaseHook()
		Expect(err).To(BeNil())
		Expect(hookCommand).To(Equal(expectedHookCommand))
	}, Entry("has pre_release_hook", `spec_version: 2
module:
  language: Python
  scripts:
    pre_release_hook: "python manage.py migrate --no-input"
  processes:
    web:
      command: python manage.py runserver
`, "python manage.py migrate --no-input"), Entry("no pre_release_hook", `spec_version: 2
module:
  language: Python
  scripts:
    test: "python"`, ""), Entry("no scripts", `spec_version: 2`, ""))
})
