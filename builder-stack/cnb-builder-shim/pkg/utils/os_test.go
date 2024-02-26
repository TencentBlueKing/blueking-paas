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
	Describe("Test file utils", func() {
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
})
