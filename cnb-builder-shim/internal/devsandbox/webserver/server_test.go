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

	_ = config.InitConfig()

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
	})

	AfterEach(func() {
		_ = os.RemoveAll(tmpUploadDir)
		_ = os.Setenv("UPLOAD_DIR", oldUploadDir)
	})

	Describe("deploy", func() {
		It("deploy app", func() {
			srcPath := filepath.Join("service", "testdata", "helloworld.zip")

			file, _ := os.Open(srcPath)
			defer file.Close()

			body := &bytes.Buffer{}
			writer := multipart.NewWriter(body)
			part, _ := writer.CreateFormFile("file", filepath.Base(srcPath))
			_, _ = io.Copy(part, file)
			_ = writer.Close()

			w := httptest.NewRecorder()
			req, _ := http.NewRequest("POST", "/deploys", body)
			req.Header.Set("Content-Type", writer.FormDataContentType())
			req.Header.Set("Authorization", "Bearer jwram1lpbnuugmcv")

			s.server.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(200))
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
})
