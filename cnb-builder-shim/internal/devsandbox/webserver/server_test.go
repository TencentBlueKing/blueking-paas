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

package webserver

import (
	"bytes"
	"encoding/json"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"

	"github.com/caarlos0/env/v10"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/config"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/webserver/service"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
)

var _ = Describe("Test webserver api", func() {
	var s *WebServer
	var tmpUploadDir string

	lg := logging.Default()

	oldUploadDir := os.Getenv("UPLOAD_DIR")

	_ = config.Init()

	BeforeEach(func() {
		tmpUploadDir, _ = os.MkdirTemp("", "upload")
		_ = os.Setenv("UPLOAD_DIR", tmpUploadDir)

		cfg := envConfig{}
		_ = env.Parse(&cfg)

		r := gin.Default()
		r.Use(tokenAuthMiddleware(cfg.Token))
		s = &WebServer{
			server: r,
			lg:     &lg,
			ch:     make(chan devsandbox.AppReloadEvent, 1),
			env:    cfg,
		}

		mgr := &service.FakeDeployManger{}
		r.POST("/deploys", DeployHandler(s, mgr))
		r.GET("/deploys/:deployID/results", ResultHandler(mgr))
		r.GET("/settings", SettingsHandler())
	})

	AfterEach(func() {
		_ = os.RemoveAll(tmpUploadDir)
		_ = os.Setenv("UPLOAD_DIR", oldUploadDir)
	})

	Describe("deploy", func() {
		Context("deploy with env_vars", func() {
			testCases := []struct {
				name      string
				envVars   string
				expected  map[string]string
				expectErr bool
			}{
				{
					name:     "with valid env_vars",
					envVars:  `{"ENV_VAR1":"value1","ENV_VAR2":"value2"}`,
					expected: map[string]string{"ENV_VAR1": "value1", "ENV_VAR2": "value2"},
				},
				{
					name:     "with empty env_vars string",
					envVars:  "",
					expected: map[string]string{},
				},
				{
					name:     "with empty JSON object",
					envVars:  "{}",
					expected: map[string]string{},
				},
				{
					name:      "with invalid JSON format",
					envVars:   `{invalid:json}`,
					expected:  nil,
					expectErr: true,
				},
			}

			for _, tc := range testCases {
				It(tc.name, func() {
					srcPath := filepath.Join("service", "testdata", "helloworld.zip")
					file, err := os.Open(srcPath)
					Expect(err).NotTo(HaveOccurred())
					defer file.Close()

					body := &bytes.Buffer{}
					writer := multipart.NewWriter(body)
					part, _ := writer.CreateFormFile("file", filepath.Base(srcPath))
					_, _ = io.Copy(part, file)
					_ = writer.WriteField("env_vars", tc.envVars)
					_ = writer.Close()

					w := httptest.NewRecorder()
					req, _ := http.NewRequest("POST", "/deploys", body)
					req.Header.Set("Content-Type", writer.FormDataContentType())
					req.Header.Set("Authorization", "Bearer jwram1lpbnuugmcv")

					s.server.ServeHTTP(w, req)

					if tc.expectErr {
						Expect(w.Code).To(Equal(400))
					} else {
						Expect(w.Code).To(Equal(200))

						select {
						case event := <-s.ch:
							Expect(event.EnvVars).To(Equal(tc.expected))
						default:
							Fail("No event received")
						}
					}
				})
			}
		})

		It("get deploy result", func() {
			deployID := uuid.NewString()
			w := httptest.NewRecorder()
			req, _ := http.NewRequest("GET", "/deploys/"+deployID+"/results?log=true", nil)
			req.Header.Set("Authorization", "Bearer jwram1lpbnuugmcv")

			s.server.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(200))
			Expect(w.Body.String()).To(ContainSubstring(`"status":"Success"`))
			Expect(w.Body.String()).To(ContainSubstring(`"log":"build done..."`))
		})

		It("get deploy result without token", func() {
			deployID := uuid.NewString()
			w := httptest.NewRecorder()
			req, _ := http.NewRequest("GET", "/deploys/"+deployID+"/results?log=true", nil)

			s.server.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(401))
		})
	})

	Describe("get settings.json", func() {
		// 这里需要在单测中覆盖包级变量来模拟 settings 路径，因为：
		// 1. settings API 中的 "/coder/code-server/User" 是写死的，而根目录 "/" 是只读的：'mkdir /coder: read-only file system'
		// 2. 在单测中普通用户没有权限创建 /coder 这样的顶级目录，因此需要使用临时目录来模拟固定路径
		// 3. 由于 settings.json 的路径固定，所以需要通过覆盖包级变量来设置 API 读取的路径

		var (
			tmpSettingsDir      string
			originalSettingsDir string
		)

		BeforeEach(func() {
			originalSettingsDir = SettingsDirPath

			var err error
			tmpSettingsDir, err = os.MkdirTemp("", "settings-test")
			Expect(err).NotTo(HaveOccurred())

			// 覆盖包级变量
			SettingsDirPath = tmpSettingsDir
		})

		AfterEach(func() {
			SettingsDirPath = originalSettingsDir
			os.RemoveAll(tmpSettingsDir)
		})

		getSettingsPath := func() string {
			return filepath.Join(SettingsDirPath, SettingsFileName)
		}

		Context("settings.json does not exist", func() {
			It("should return 404 Not Found", func() {
				req, _ := http.NewRequest("GET", "/settings", nil)
				req.Header.Set("Authorization", "Bearer jwram1lpbnuugmcv")
				w := httptest.NewRecorder()
				s.server.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusNotFound))
				Expect(w.Body.String()).To(ContainSubstring("配置文件不存在"))
			})
		})

		Context("settings.json is too large", func() {
			BeforeEach(func() {
				settingsPath := getSettingsPath()

				// 创建大小超过 2MB 的文件
				f, err := os.Create(settingsPath)
				Expect(err).NotTo(HaveOccurred())
				defer f.Close()

				// 写入超过 2MB 的数据
				data := make([]byte, 3*1024*1024)
				_, err = f.Write(data)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should return 400 Bad Request", func() {
				req, _ := http.NewRequest("GET", "/settings", nil)
				req.Header.Set("Authorization", "Bearer jwram1lpbnuugmcv")
				w := httptest.NewRecorder()
				s.server.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusBadRequest))

				var resp map[string]string
				err := json.Unmarshal(w.Body.Bytes(), &resp)
				Expect(err).NotTo(HaveOccurred())

				Expect(resp["error"]).To(ContainSubstring("配置文件过大"))
				Expect(resp["error"]).To(ContainSubstring("3.0MB"))
				Expect(resp["error"]).To(ContainSubstring("2.0MB"))
			})
		})

		Context("settings.json is valid", func() {
			const validSettings = `{
			"editor.fontSize": 14,
			"workbench.colorTheme": "Default Dark+",
			"git.confirmSync": false
		}`

			BeforeEach(func() {
				settingsPath := getSettingsPath()

				err := os.WriteFile(settingsPath, []byte(validSettings), 0644)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should return the file content with correct headers", func() {
				req, _ := http.NewRequest("GET", "/settings", nil)
				req.Header.Set("Authorization", "Bearer jwram1lpbnuugmcv")
				w := httptest.NewRecorder()
				s.server.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusOK))
				Expect(w.Header().Get("Content-Type")).To(Equal("application/json"))
				Expect(w.Body.String()).To(Equal(validSettings))
			})
		})

		Context("file is a directory", func() {
			BeforeEach(func() {
				settingsPath := getSettingsPath()

				if _, err := os.Stat(settingsPath); err == nil {
					os.Remove(settingsPath)
				}

				// 创建名为 settings.json 的目录
				err := os.Mkdir(settingsPath, 0755)
				Expect(err).NotTo(HaveOccurred())
			})

			It("should return 500 Internal Server Error", func() {
				req, _ := http.NewRequest("GET", "/settings", nil)
				req.Header.Set("Authorization", "Bearer jwram1lpbnuugmcv")
				w := httptest.NewRecorder()
				s.server.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusInternalServerError))
				Expect(w.Body.String()).To(ContainSubstring("读取文件失败"))
			})
		})
	})
})
