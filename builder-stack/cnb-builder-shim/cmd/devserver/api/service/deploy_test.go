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

package service

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Test DeployManager", func() {
	mgr := DeployManager{}

	Context("test generateProcfile", func() {
		var tmpDir string
		var err error

		BeforeEach(func() {
			tmpDir, err = os.MkdirTemp("", "app_src")
			Expect(err).To(BeNil())
		})

		AfterEach(func() {
			Expect(os.RemoveAll(tmpDir)).To(BeNil())
		})

		It("test generateProcfile success", func() {
			appDescYaml := `spec_version: 2
module:
 language: Python
 scripts:
   pre_release_hook: "python manage.py migrate --no-input"
 processes:
   web:
     command: python manage.py runserver
   celery:
     command: celery -A app worker -l info
`
			expectedWebProcContent := "web: python manage.py runserver"
			expectedCeleryProcContent := "celery: celery -A app worker -l info"

			Expect(os.WriteFile(filepath.Join(tmpDir, "app_desc.yaml"), []byte(appDescYaml), 0644)).To(BeNil())
			Expect(mgr.generateProcfile(tmpDir)).To(BeNil())

			procFileContent, _ := os.ReadFile(filepath.Join(tmpDir, "Procfile"))
			Expect(string(procFileContent)).To(ContainSubstring(expectedWebProcContent))
			Expect(string(procFileContent)).To(ContainSubstring(expectedCeleryProcContent))
		})

		It("test generateProcfile fail", func() {
			appDescYaml := `spec_version: 2`
			Expect(os.WriteFile(filepath.Join(tmpDir, "app_desc.yaml"), []byte(appDescYaml), 0644)).To(BeNil())
			Expect(mgr.generateProcfile(tmpDir)).NotTo(HaveOccurred())
		})
	})
	Context("test makeSyncScript", func() {
		It("test makeSyncScript success", func() {
			expectedScript := `#! /bin/bash

rm -rf /app/*
mv /tmp/xxx/app/* /app/
chown -R cnb.cnb /app

rm -rf /tmp/xxx/app

echo "code sync done"
`
			Expect(mgr.makeSyncScript("/tmp/xxx/app", "/app")).To(Equal(expectedScript))
		})

	})
})
