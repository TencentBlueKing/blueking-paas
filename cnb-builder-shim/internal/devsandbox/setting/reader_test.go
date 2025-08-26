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

package setting

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("TestReader", func() {
	var (
		tmpDir string
		reader *UserSettingsReader
	)

	BeforeEach(func() {
		tmpDir, _ = os.MkdirTemp("", "test-settings")
		reader = &UserSettingsReader{Dir: tmpDir}
	})

	AfterEach(func() {
		_ = os.RemoveAll(tmpDir)
		_ = os.Unsetenv(UserSettingsSizeEnvVarKey)
	})

	Describe("Read", func() {
		Context("when settings file does not exist", func() {
			It("should return 'configuration file not found' error", func() {
				_, err := reader.Read()
				Expect(err).To(MatchError(UserSettingsNotFound))
			})
		})

		Context("when settings file is too large", func() {
			BeforeEach(func() {
				filePath := filepath.Join(tmpDir, UserSettingsFileName)
				f, err := os.Create(filePath)
				Expect(err).NotTo(HaveOccurred())
				defer f.Close()

				data := make([]byte, 600*1024)
				_, err = f.Write(data)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should return 'configuration file is too large' error", func() {
				_, err := reader.Read()
				Expect(err).To(MatchError(UserSettingsTooLarge))
			})
		})

		Context("when json is valid", func() {
			BeforeEach(func() {
				filePath := filepath.Join(tmpDir, UserSettingsFileName)
				Expect(os.WriteFile(filePath, []byte(`{"theme": "dark"}`), 0644)).To(Succeed())
			})

			It("should return the parsed JSON", func() {
				settingsMap, err := reader.Read()
				Expect(err).NotTo(HaveOccurred())
				Expect(settingsMap).To(HaveKeyWithValue("theme", "dark"))
			})
		})

		Context("when file is a directory", func() {
			BeforeEach(func() {
				filePath := filepath.Join(tmpDir, UserSettingsFileName)
				Expect(os.Mkdir(filePath, 0755)).To(Succeed())
			})

			It("should return 'is a directory' error", func() {
				_, err := reader.Read()
				Expect(err).To(HaveOccurred())
				Expect(err.Error()).To(ContainSubstring("is a directory"))
			})
		})

		Context("when json is invalid", func() {
			BeforeEach(func() {
				filePath := filepath.Join(tmpDir, UserSettingsFileName)
				Expect(os.WriteFile(filePath, []byte("{invalid json}"), 0644)).To(Succeed())
			})

			It("should return 'parse settings.json' error", func() {
				_, err := reader.Read()
				Expect(err).To(HaveOccurred())
				Expect(err.Error()).To(ContainSubstring("parse settings.json"))
			})
		})

		Context("with custom max size via environment variable", func() {
			BeforeEach(func() {
				_ = os.Setenv(UserSettingsSizeEnvVarKey, "1024")

				filePath := filepath.Join(tmpDir, UserSettingsFileName)
				content := fmt.Sprintf(`{"largeData": "%s"}`, strings.Repeat(" ", 800*1024))
				err := os.WriteFile(filePath, []byte(content), 0644)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should allow files under custom limit", func() {
				_, err := reader.Read()
				Expect(err).NotTo(HaveOccurred())
			})
		})

		Context("with invalid environment variable value", func() {
			BeforeEach(func() {
				_ = os.Setenv(UserSettingsSizeEnvVarKey, "invalid")

				filePath := filepath.Join(tmpDir, UserSettingsFileName)
				Expect(os.WriteFile(filePath, []byte("{}"), 0644)).To(Succeed())
			})

			It("should fallback to default size", func() {
				_, err := reader.Read()
				Expect(err).NotTo(HaveOccurred())
			})
		})
	})
})
