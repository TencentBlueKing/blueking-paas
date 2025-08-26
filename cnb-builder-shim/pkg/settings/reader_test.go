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

package settings

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"os"
	"path/filepath"
	"testing"
)

func TestSettings(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "Settings Suite")
}

var _ = Describe("TestReader", func() {
	var (
		tmpDir string
		reader Reader
	)

	BeforeEach(func() {
		var err error
		tmpDir, err = os.MkdirTemp("", "settings-test")
		Expect(err).NotTo(HaveOccurred())
		reader = NewReader(tmpDir)
	})

	AfterEach(func() {
		os.RemoveAll(tmpDir)
		os.Unsetenv(UserSettingsSizeEnvVarKey)
	})

	Describe("Read", func() {
		Context("when json does not exist", func() {
			It("should return 'configuration file not found' error", func() {
				_, err := reader.Read()
				Expect(err).To(HaveOccurred())
				Expect(err).To(MatchError(UserSettingsNotFound))
			})
		})

		Context("when json is valid", func() {
			const validSettings = `{"theme": "dark"}`

			BeforeEach(func() {
				filePath := filepath.Join(tmpDir, UserSettingsFileName)
				Expect(os.WriteFile(filePath, []byte(validSettings), 0644)).To(Succeed())
			})

			It("should return the parsed JSON", func() {
				settingsMap, err := reader.Read()
				Expect(err).NotTo(HaveOccurred())
				Expect(settingsMap).To(HaveKeyWithValue("theme", "dark"))
			})
		})

		Context("when json is too large", func() {
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
				Expect(err).To(HaveOccurred())
				Expect(err).To(MatchError(UserSettingsTooLarge))
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

			It("should return 'failed to parse settings.json' error", func() {
				_, err := reader.Read()
				Expect(err).To(HaveOccurred())
				Expect(err.Error()).To(ContainSubstring("failed to parse settings.json"))
			})
		})

		Context("with custom max size via environment variable", func() {
			BeforeEach(func() {
				os.Setenv(UserSettingsSizeEnvVarKey, "1024")

				filePath := filepath.Join(tmpDir, UserSettingsFileName)

				content := []byte(`{"largeData": "`)
				spaces := make([]byte, 799*1024)
				for i := range spaces {
					spaces[i] = ' '
				}
				content = append(content, spaces...)
				content = append(content, `"}`...)

				err := os.WriteFile(filePath, content, 0644)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should allow files under custom limit", func() {
				_, err := reader.Read()
				Expect(err).NotTo(HaveOccurred())
			})
		})

		Context("with invalid environment variable value", func() {
			BeforeEach(func() {
				os.Setenv(UserSettingsSizeEnvVarKey, "invalid")

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
