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

package account_test

import (
	"errors"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/account"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/apiresources"
)

var _ = Describe("TestConfig", func() {
	BeforeEach(func() {
		apiresources.DefaultRequester = &apiresources.MockedRequester{}
	})

	DescribeTable(
		"TestFetchUsernameByAccessToken",
		func(accessToken, exceptedUsername string, exceptedErr error) {
			username, err := account.FetchUserNameByAccessToken(accessToken)
			Expect(username).To(Equal(username))
			Expect(errors.Is(err, exceptedErr)).To(BeTrue())
		},
		Entry("auth api err case", "cause_auth_err", "", apiresources.AuthApiErr),
		Entry("resp format err case", "cause_auth_resp_err", "", apiresources.AuthApiRespErr),
		Entry("invalid access token case", "invalid_token", "", account.TokenExpiredOrInvalid),
		Entry("no username err case", "no_username", "", account.FetchUsernameFailedErr),
		Entry("username in rtx case", "username_in_rtx", "admin1", nil),
		Entry("username in uin case", "username_in_uin", "admin2", nil),
	)

	DescribeTable(
		"TestIsUserAuthorized",
		func(accessToken string, authorized bool) {
			Expect(account.IsUserAuthorized(accessToken)).To(Equal(authorized))
		},
		Entry("auth api err case", "cause_auth_err", false),
		Entry("resp format err case", "cause_auth_resp_err", false),
		Entry("invalid access token case", "invalid_token", false),
		Entry("no username err case", "no_username", false),
		Entry("username in rtx case", "username_in_rtx", true),
		Entry("username in uin case", "username_in_uin", true),
	)
})
