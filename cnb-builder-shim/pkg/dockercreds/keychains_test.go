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
	"os"

	"github.com/google/go-containerregistry/pkg/authn"
	"github.com/google/go-containerregistry/pkg/name"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("TestCase", func() {
	var (
		reference = name.MustParseReference("mirrors.tencent.com/foo/bar", name.WeakValidation)
	)

	Describe("Test EnvKeychain", func() {
		It("env var exists", func() {
			defer os.Unsetenv(EnvRegistryAuth)
			os.Setenv(EnvRegistryAuth, `{"mirrors.tencent.com": "Basic Zm9v"}`)
			keychain, err := NewEnvKeychain(EnvRegistryAuth)
			Expect(err).To(BeNil())

			auth, err := keychain.Resolve(reference.Context())
			Expect(auth).To(Not(Equal(authn.Anonymous)))
			Expect(err).To(BeNil())
		})

		It("env var with full repository name exists", func() {
			defer os.Unsetenv(EnvRegistryAuth)
			os.Setenv(EnvRegistryAuth, `{"mirrors.tencent.com/foo/bar": "Basic Zm9v"}`)
			keychain, err := NewEnvKeychain(EnvRegistryAuth)
			Expect(err).To(BeNil())

			auth, err := keychain.Resolve(reference.Context())
			Expect(auth).To(Not(Equal(authn.Anonymous)))
			Expect(err).To(BeNil())
		})

		It("env var not exists", func() {
			keychain, err := NewEnvKeychain(EnvRegistryAuth)
			Expect(err).To(BeNil())

			auth, err := keychain.Resolve(reference.Context())
			Expect(auth).To(Equal(authn.Anonymous))
			Expect(err).To(BeNil())
		})

		It("wrong env var", func() {
			defer os.Unsetenv(EnvRegistryAuth)
			os.Setenv(EnvRegistryAuth, `[{"mirrors.tencent.com": "Basic Zm9v"}]`)
			_, err := NewEnvKeychain(EnvRegistryAuth)
			Expect(err.Error()).To(ContainSubstring("failed to parse CNB_REGISTRY_AUTH value"))
		})
	})

})
