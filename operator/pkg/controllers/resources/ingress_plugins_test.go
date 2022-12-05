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
	"github.com/lithammer/dedent"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/testing"
)

var _ = Describe("Test ingress_plugins.go", func() {
	var bkapp *paasv1alpha1.BkApp

	BeforeEach(func() {
		bkapp = &paasv1alpha1.BkApp{
			TypeMeta:   metav1.TypeMeta{Kind: paasv1alpha1.KindBkApp, APIVersion: paasv1alpha1.GroupVersion.String()},
			ObjectMeta: metav1.ObjectMeta{Name: "demo", Namespace: "default", Annotations: map[string]string{}},
			Spec:       paasv1alpha1.AppSpec{},
		}
	})

	Context("test AccessControlPlugin", func() {
		DescribeTable("test MakeServerSnippet", func(initAction func(), expected string) {
			By("init", initAction)

			var plugin NginxIngressPlugin = &AccessControlPlugin{
				Config: &paasv1alpha1.AccessControlConfig{RedisConfigKey: "acc_redis_server_name"},
			}
			Expect(plugin.MakeServerSnippet(bkapp, nil)).To(Equal(expected))
		},
			Entry("when without app metadata", func() {}, ""),
			Entry("when missing AccessControlAnnoKey", func() { testing.WithAppInfoAnnotations(bkapp) }, ""),
			Entry("when disable acl", func() {
				testing.WithAppInfoAnnotations(bkapp)
				bkapp.Annotations[paasv1alpha1.AccessControlAnnoKey] = "false"
			}, ""),
			Entry("normal case", func() {
				testing.WithAppInfoAnnotations(bkapp)
				bkapp.Annotations[paasv1alpha1.AccessControlAnnoKey] = "true"
			}, dedent.Dedent(`
        # Blow content was configured by access-control plugin, do not edit

        set $bkapp_app_code 'region-bkapp-app-code-stag';
        set $bkapp_bk_app_code 'app-code';
        set $bkapp_region 'region';
        set $bkapp_env_name 'stag';

        set $acc_redis_server_name 'acc_redis_server_name';

        access_by_lua_file $module_access_path/main.lua;

        # content of access-control plugin ends`)),
		)

		It("test MakeConfigurationSnippet", func() {
			var plugin NginxIngressPlugin = &AccessControlPlugin{
				Config: &paasv1alpha1.AccessControlConfig{RedisConfigKey: "local"},
			}
			Expect(plugin.MakeConfigurationSnippet(bkapp, nil)).To(Equal(""))
		})
	})
})
