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
package http_test

import (
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"path/filepath"
	"time"

	"github.com/go-logr/logr"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	putHttp "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/putter/http"
)

var basePath = "../testdata"

var _ = Describe("Http", func() {
	var (
		logger logr.Logger
		server *httptest.Server
		client *putHttp.Putter
	)

	BeforeEach(func() {
		logger = logr.Discard()
		client = putHttp.NewPutter(logger)
	})
	AfterEach(func() {
		if server != nil {
			server.Close()
		}
	})

	Context("successful uploads", func() {
		BeforeEach(func() {
			server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				Expect(r.Method).To(Equal(http.MethodPut))
				body, err := io.ReadAll(r.Body)
				Expect(err).NotTo(HaveOccurred())
				defer r.Body.Close()

				Expect(len(body)).To(BeNumerically(">", 0))
				w.WriteHeader(http.StatusOK)
			}))
		})

		DescribeTable("should successfully upload files",
			func(srcFileName string) {
				srcPath := filepath.Join(basePath, srcFileName)
				destUrl, err := url.Parse(server.URL)
				Expect(err).To(BeNil())

				err = client.Put(srcPath, destUrl)
				Expect(err).To(BeNil())
			},
			Entry("upload project.tgz", "project.tgz"),
		)
	})

	Context("error scenarios", func() {
		It("should return error when server returns 404", func() {
			server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(http.StatusNotFound)
			}))

			srcPath := filepath.Join(basePath, "project.tgz")
			destUrl, _ := url.Parse(server.URL)

			err := client.Put(srcPath, destUrl)
			Expect(err).To(HaveOccurred())
			Expect(err.Error()).To(ContainSubstring("Failed to upload to bkrepo: HTTP 404"))
		})

		It("should return error when server returns 500", func() {
			server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(http.StatusInternalServerError)
				w.Write([]byte("Internal server error"))
			}))

			srcPath := filepath.Join(basePath, "project.tgz")
			destUrl, _ := url.Parse(server.URL)

			err := client.Put(srcPath, destUrl)
			Expect(err).To(HaveOccurred())
			Expect(err.Error()).To(ContainSubstring("Failed to upload to bkrepo: HTTP 500"))
		})

		It("should return error when server is unreachable", func() {
			srcPath := filepath.Join(basePath, "project.tgz")
			destUrl, _ := url.Parse("http://invalid-url-that-does-not-exist")

			err := client.Put(srcPath, destUrl)
			Expect(err).To(HaveOccurred())
		})

		It("should return error when URL is invalid", func() {
			srcPath := filepath.Join(basePath, "project.tgz")
			invalidUrl := &url.URL{Host: "invalid:host:with:colons"}

			err := client.Put(srcPath, invalidUrl)
			Expect(err).To(HaveOccurred())
		})
	})

	Context("timeout scenarios", func() {
		It("should handle slow server response", func() {
			server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				time.Sleep(100 * time.Millisecond)
				w.WriteHeader(http.StatusOK)
			}))

			srcPath := filepath.Join(basePath, "project.tgz")
			destUrl, _ := url.Parse(server.URL)

			err := client.Put(srcPath, destUrl)
			Expect(err).To(BeNil())
		})
	})
})
