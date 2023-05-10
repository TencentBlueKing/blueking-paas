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

package handler_test

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/apiresources"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/handler"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/model"
)

var _ = Describe("TestList", func() {
	BeforeEach(func() {
		apiresources.DefaultRequester = &apiresources.MockedRequester{}
	})

	It("TestAppLister", func() {
		excepted := model.MinimalApplications{
			Total: 2,
			Apps: []model.AppBasicInfo{
				{Code: "test-code-1", Name: "test-app-1"},
				{Code: "test-code-2", Name: "test-app-2"},
			},
		}

		lister := handler.NewAppLister()
		result, err := lister.Exec()
		Expect(result).To(Equal(excepted))
		Expect(err).To(BeNil())

		Expect(result.String() != "").To(BeTrue())
	})
})
