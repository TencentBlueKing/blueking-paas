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

package apiresources

// MockedRequester Mocked api 调用入口
type MockedRequester struct{}

func (r MockedRequester) CheckToken(accessToken string) (map[string]any, error) {
	// 请求失败的情况
	if accessToken == "cause_auth_err" {
		return nil, AuthApiErr
	}

	// 结果解析异常的情况
	if accessToken == "cause_auth_resp_err" {
		return nil, AuthApiRespErr
	}

	// 不合法的 AccessToken
	if accessToken == "invalid_token" {
		return map[string]any{
			"result": false,
			"data":   nil,
		}, nil
	}

	// 请求成功，但是没有用户信息
	if accessToken == "no_username" {
		return map[string]any{
			"result": true,
			"data": map[string]any{
				"id_providers": map[string]any{
					"rtx": map[string]any{
						"username": "",
					},
					"uin": map[string]any{
						"username": "",
					},
				},
			},
		}, nil
	}

	// 请求正常，用户信息在 rtx 字段
	if accessToken == "username_in_rtx" {
		return map[string]any{
			"result": true,
			"data": map[string]any{
				"id_providers": map[string]any{
					"rtx": map[string]any{
						"username": "admin1",
					},
					"uin": map[string]any{
						"username": "",
					},
				},
			},
		}, nil
	}

	// 请求正常，用户信息在 uin 字段
	return map[string]any{
		"result": true,
		"data": map[string]any{
			"id_providers": map[string]any{
				"rtx": map[string]any{
					"username": "",
				},
				"uin": map[string]any{
					"username": "admin2",
				},
			},
		},
	}, nil
}
