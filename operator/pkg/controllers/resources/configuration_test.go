/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *	http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package resources

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

var _ = Describe("Get App Envs", func() {
	var bkapp *paasv1alpha2.BkApp
	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: paasv1alpha2.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:        "bkapp-sample",
				Namespace:   "default",
				Annotations: map[string]string{},
			},
			Spec: paasv1alpha2.AppSpec{
				Configuration: paasv1alpha2.AppConfig{
					Env: []paasv1alpha2.AppEnvVar{
						{Name: "ENV_NAME_1", Value: "env_value_1"},
						{Name: "ENV_NAME_2", Value: "env_value_2"},
					},
				},
			},
		}
	})

	It("normal case", func() {
		envs := GetAppEnvs(bkapp)
		Expect(len(envs)).To(Equal(2))

		for idx, env := range envs {
			Expect(env.Name).To(Equal(bkapp.Spec.Configuration.Env[idx].Name))
			Expect(env.Value).To(Equal(bkapp.Spec.Configuration.Env[idx].Value))
		}
	})

	It("no env", func() {
		bkapp.Spec.Configuration.Env = []paasv1alpha2.AppEnvVar{}
		envs := GetAppEnvs(bkapp)
		Expect(len(envs)).To(Equal(0))
	})
})
