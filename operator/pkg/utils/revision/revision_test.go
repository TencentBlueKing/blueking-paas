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

package revision

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/onsi/gomega/types"
	appsv1 "k8s.io/api/apps/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	"bk.tencent.com/paas-app-operator/api/v1alpha2"
)

var _ = Describe("Test revision tools", func() {
	DescribeTable("test GetRevision", func(obj metav1.Object, errMatcher types.GomegaMatcher, expected int64) {
		revision, err := GetRevision(obj)
		Expect(err).To(errMatcher)
		Expect(revision).To(Equal(expected))
	},
		Entry("RevisionAnnoKey undefined", &metav1.ObjectMeta{
			Annotations: map[string]string{},
		}, Not(HaveOccurred()), int64(0)),
		Entry("RevisionAnnoKey = 1", &metav1.ObjectMeta{
			Annotations: map[string]string{v1alpha2.RevisionAnnoKey: "1"},
		}, Not(HaveOccurred()), int64(1)),
		Entry("RevisionAnnoKey = 2", &metav1.ObjectMeta{
			Annotations: map[string]string{v1alpha2.RevisionAnnoKey: "2"},
		}, Not(HaveOccurred()), int64(2)),
		Entry("invalid RevisionAnnoKey", &metav1.ObjectMeta{
			Annotations: map[string]string{v1alpha2.RevisionAnnoKey: "xxx"},
		}, HaveOccurred(), int64(0)),
	)

	DescribeTable("test MaxRevision", func(objs []*appsv1.Deployment, expected int64) {
		Expect(MaxRevision(objs)).To(Equal(expected))
	},
		Entry("empty slice", nil, int64(0)),
		Entry("RevisionAnnoKey undefined", []*appsv1.Deployment{
			{},
		}, int64(0)),
		Entry("1", []*appsv1.Deployment{
			{
				ObjectMeta: metav1.ObjectMeta{
					Annotations: map[string]string{
						v1alpha2.RevisionAnnoKey: "1",
					},
				},
			},
		}, int64(1)),
		Entry("1, 2 to 2", []*appsv1.Deployment{
			{
				ObjectMeta: metav1.ObjectMeta{
					Annotations: map[string]string{
						v1alpha2.RevisionAnnoKey: "1",
					},
				},
			},
			{
				ObjectMeta: metav1.ObjectMeta{
					Annotations: map[string]string{
						v1alpha2.RevisionAnnoKey: "2",
					},
				},
			},
		}, int64(2)),
		Entry("complex", []*appsv1.Deployment{
			{
				ObjectMeta: metav1.ObjectMeta{
					Annotations: map[string]string{
						v1alpha2.RevisionAnnoKey: "1",
					},
				},
			},
			{
				ObjectMeta: metav1.ObjectMeta{
					Annotations: map[string]string{
						v1alpha2.RevisionAnnoKey: "2",
					},
				},
			},
			{},
			{
				ObjectMeta: metav1.ObjectMeta{
					Annotations: map[string]string{
						v1alpha2.RevisionAnnoKey: "999",
					},
				},
			},
		}, int64(999)),
	)
})
