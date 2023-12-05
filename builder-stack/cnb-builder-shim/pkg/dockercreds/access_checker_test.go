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
package dockercreds

import (
	"fmt"
	"net/http"
	"net/http/httptest"

	"github.com/google/go-containerregistry/pkg/authn"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("TestCase", func() {
	var (
		server  *httptest.Server
		handler *http.ServeMux
		tagName string
	)

	var _ = BeforeEach(func() {
		handler = http.NewServeMux()
		server = httptest.NewServer(handler)
		tagName = fmt.Sprintf("%s/some/image:tag", server.URL[7:])
	})

	var _ = AfterEach(func() {
		server.Close()
	})

	When("VerifyWriteAccess", func() {
		It("does not error when has write access", func() {
			handler.HandleFunc("/v2/some/image/blobs/uploads/", func(writer http.ResponseWriter, request *http.Request) {
				writer.WriteHeader(201)
			})
			handler.HandleFunc("/v2/", func(writer http.ResponseWriter, request *http.Request) {
				writer.WriteHeader(200)
			})

			err := VerifyWriteAccess(testKeychain{}, tagName)
			Expect(err).To(BeNil())
		})

		It("does not error when has write access", func() {
			handler.HandleFunc("/v2/some/image/blobs/uploads/", func(writer http.ResponseWriter, request *http.Request) {
				writer.WriteHeader(403)
			})
			handler.HandleFunc("/v2/", func(writer http.ResponseWriter, request *http.Request) {
				writer.WriteHeader(200)
			})

			err := VerifyWriteAccess(testKeychain{}, tagName)
			Expect(err.Error()).To(ContainSubstring(fmt.Sprintf("POST %s/v2/some/image/blobs/uploads/: unexpected status code 403 Forbidden", server.URL)))
		})
	})

	When("#VerifyReadAccess", func() {
		It("does not error when has read access", func() {
			handler.HandleFunc("/v2/", func(writer http.ResponseWriter, request *http.Request) {
				writer.WriteHeader(200)
			})

			handler.HandleFunc("/v2/some/image/manifests/tag", func(writer http.ResponseWriter, request *http.Request) {
				writer.WriteHeader(200)
			})

			err := VerifyReadAccess(testKeychain{}, tagName)
			Expect(err).To(BeNil())
		})

		It("errors when has no read access", func() {
			handler.HandleFunc("/v2/", func(writer http.ResponseWriter, request *http.Request) {
				writer.WriteHeader(200)
			})

			handler.HandleFunc("/v2/some/image/manifests/tag", func(writer http.ResponseWriter, request *http.Request) {
				writer.WriteHeader(401)
			})

			err := VerifyReadAccess(testKeychain{}, tagName)
			Expect(err.Error()).To(Equal("UNAUTHORIZED"))
		})

		It("errors when cannot reach server", func() {
			handler.HandleFunc("/v2/", func(writer http.ResponseWriter, request *http.Request) {
				writer.WriteHeader(404)
			})

			err := VerifyReadAccess(testKeychain{}, tagName)
			Expect(err.Error()).To(ContainSubstring(fmt.Sprintf("GET %s/v2/: unexpected status code 404 Not Found", server.URL)))
		})
	})
})

type testKeychain struct {
}

func (t testKeychain) Resolve(authn.Resource) (authn.Authenticator, error) {
	return &authn.Basic{
		Username: "testUser",
		Password: "testPassword",
	}, nil
}
