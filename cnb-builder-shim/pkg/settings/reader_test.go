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
)

var _ = Describe("TestReader", func() {
	var (
		tmpDir  string
		reader  *Reader
		cleanup func()
	)

	BeforeEach(func() {
		var err error
		tmpDir, err = os.MkdirTemp("", "settings-test")
		Expect(err).NotTo(HaveOccurred())
		cleanup = func() { os.RemoveAll(tmpDir) }

		reader = NewReader(tmpDir)
	})

	AfterEach(func() {
		cleanup()
		os.Unsetenv(SizeEnvVar)
	})

	Describe("Read", func() {
		Context("when json does not exist", func() {
			It("should return 'configuration file not found' error", func() {
				_, err := reader.Read()
				Expect(err).To(HaveOccurred())
				Expect(err.Error()).To(Equal("configuration file not found"))
			})
		})

		Context("when json is valid", func() {
			const validSettings = `{"theme": "dark"}`

			BeforeEach(func() {
				filePath := filepath.Join(tmpDir, SettingsFileName)
				Expect(os.WriteFile(filePath, []byte(validSettings), 0644)).To(Succeed())
			})

			It("should return the file content", func() {
				content, err := reader.Read()
				Expect(err).NotTo(HaveOccurred())
				Expect(string(content)).To(Equal(validSettings))
			})
		})

		Context("when json is too large", func() {
			BeforeEach(func() {
				filePath := filepath.Join(tmpDir, SettingsFileName)
				f, err := os.Create(filePath)
				Expect(err).NotTo(HaveOccurred())
				defer f.Close()

				// 创建超过默认大小限制的文件 (600KB > 512KB)
				data := make([]byte, 600*1024)
				_, err = f.Write(data)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should return 'configuration file too large' error", func() {
				_, err := reader.Read()
				Expect(err).To(HaveOccurred())
				Expect(err.Error()).To(ContainSubstring("configuration file too large"))
				Expect(err.Error()).To(ContainSubstring("600.0KB"))
				Expect(err.Error()).To(ContainSubstring("512KB"))
			})
		})

		Context("when file is a directory", func() {
			BeforeEach(func() {
				filePath := filepath.Join(tmpDir, SettingsFileName)
				Expect(os.Mkdir(filePath, 0755)).To(Succeed())
			})

			It("should return 'failed to read file' error", func() {
				_, err := reader.Read()
				Expect(err).To(HaveOccurred())
				Expect(err.Error()).To(ContainSubstring("failed to read file"))
			})
		})

		Context("with custom max size via environment variable", func() {
			BeforeEach(func() {
				os.Setenv(SizeEnvVar, "1024") // 1MB

				filePath := filepath.Join(tmpDir, SettingsFileName)
				f, err := os.Create(filePath)
				Expect(err).NotTo(HaveOccurred())
				defer f.Close()

				// 创建 800KB 文件
				data := make([]byte, 800*1024)
				_, err = f.Write(data)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should allow files under custom limit", func() {
				_, err := reader.Read()
				Expect(err).NotTo(HaveOccurred())
			})
		})

		Context("with invalid environment variable value", func() {
			BeforeEach(func() {
				os.Setenv(SizeEnvVar, "invalid")

				filePath := filepath.Join(tmpDir, SettingsFileName)
				Expect(os.WriteFile(filePath, []byte("{}"), 0644)).To(Succeed())
			})

			It("should fallback to default size", func() {
				_, err := reader.Read()
				Expect(err).NotTo(HaveOccurred())
			})
		})

		Context("with negative environment variable value", func() {
			BeforeEach(func() {
				os.Setenv(SizeEnvVar, "-100")

				filePath := filepath.Join(tmpDir, SettingsFileName)
				Expect(os.WriteFile(filePath, []byte("{}"), 0644)).To(Succeed())
			})

			It("should fallback to default size", func() {
				_, err := reader.Read()
				Expect(err).NotTo(HaveOccurred())
			})
		})

		Context("with zero environment variable value", func() {
			BeforeEach(func() {
				os.Setenv(SizeEnvVar, "0")

				filePath := filepath.Join(tmpDir, SettingsFileName)
				Expect(os.WriteFile(filePath, []byte("{}"), 0644)).To(Succeed())
			})

			It("should fallback to default size", func() {
				_, err := reader.Read()
				Expect(err).NotTo(HaveOccurred())
			})
		})
	})
})
