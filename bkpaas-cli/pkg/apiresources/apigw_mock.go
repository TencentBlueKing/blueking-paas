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

// CheckToken ...
func (r MockedRequester) CheckToken(accessToken string) (map[string]any, error) {
	switch accessToken {
	// 请求失败的情况
	case "auth_api_error":
		return nil, AuthApiErr
	// 结果解析异常的情况
	case "auth_resp_error":
		return nil, ApiRespDecodeErr
	// 不合法的 AccessToken
	case "invalid_token":
		return map[string]any{"result": false, "data": nil}, nil
	// 请求成功，但是没有用户信息
	case "no_username":
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
	// 请求正常，用户信息在 rtx 字段
	case "username_in_rtx":
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
	// 请求正常，用户信息在 uin 字段
	default:
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
}

// ListAppMinimal ...
func (r MockedRequester) ListAppMinimal() (map[string]any, error) {
	return map[string]any{
		"count": 2,
		"results": []any{
			map[string]any{
				"application": map[string]any{
					"code": "test-code-1",
					"name": "test-app-1",
				},
			},
			map[string]any{
				"application": map[string]any{
					"code": "test-code-2",
					"name": "test-app-2",
				},
			},
		},
	}, nil
}

// GetAppInfo ...
func (r MockedRequester) GetAppInfo(appCode string) (map[string]any, error) {
	if appCode == "no_exists" {
		return nil, PaaSApiErr
	}

	return map[string]any{
		"application": map[string]any{
			"code":        appCode,
			"name":        "test-app",
			"region":      "region",
			"region_name": "默认版",
			"type":        "default",
			"modules": []any{
				map[string]any{
					"name": "default",
					"repo": map[string]any{
						"type":         "github",
						"display_name": "Opensource Community Github",
						"repo_url":     "https://github.com/octocat/Hello-World.git",
					},
					"clusters": map[string]any{
						"stag": map[string]any{
							"name":           "default",
							"bcs_cluster_id": "BCS-K8S-12345",
						},
					},
				},
			},
		},
	}, nil
}

// DeployDefaultApp ...
func (r MockedRequester) DeployDefaultApp(appCode, appModule, deployEnv, branch string) (map[string]any, error) {
	return map[string]any{
		"deployment_id": "b2d4cccc-f535-4282-9b8c-74162e817413",
	}, nil
}

// GetDefaultAppDeployResult ...
func (r MockedRequester) GetDefaultAppDeployResult(appCode, appModule, deployID string) (map[string]any, error) {
	return map[string]any{
		"status":       "failed",
		"logs":         "Can not read Procfile file from repository",
		"error_detail": "Procfile error: Can not read Procfile file from repository",
		"error_tips": map[string]any{
			"helpers": []any{
				map[string]any{
					"link": "https://wiki.example.com?pageId=how-to-fix-procfile",
					"text": "How to fix Procfile",
				},
			},
		},
	}, nil
}

// ListDefaultAppDeployHistory ...
func (r MockedRequester) ListDefaultAppDeployHistory(appCode, appModule string) (map[string]any, error) {
	return map[string]any{
		"count": 2,
		"results": []any{
			map[string]any{
				"id":     "b1ffd86d-b854-4c79-9bb0-d1e8021e17ed",
				"status": "successful",
				"operator": map[string]any{
					"username": "admin",
				},
				"created":       "2023-04-17 16:28:35",
				"start_time":    "2023-04-17 16:28:36",
				"complete_time": "2023-04-17 16:29:09",
				"deployment_id": "b1ffd86d-b854-4c79-9bb0-d1e8021e17ed",
				"environment":   "stag",
				"repo": map[string]any{
					"source_type": "github",
					"type":        "branch",
					"name":        "dev-1",
					"url":         "https://github.com/octocat/Hello-World.git",
					"revision":    "3f89690ac2bb68f10de70a610a60c5e7c49c783d",
				},
			},
			map[string]any{
				"id":     "45bce562-5b40-42a3-a0ac-69668bcdbe74",
				"status": "failed",
				"operator": map[string]any{
					"username": "admin",
				},
				"created":       "2023-04-17 16:25:05",
				"start_time":    "2023-04-17 16:25:06",
				"complete_time": "2023-04-17 16:25:06",
				"deployment_id": "45bce562-5b40-42a3-a0ac-69668bcdbe74",
				"environment":   "stag",
				"repo": map[string]any{
					"source_type": "github",
					"type":        "branch",
					"name":        "dev-2",
					"url":         "https://github.com/octocat/Hello-World.git",
					"revision":    "3f89690ac2bb68f10de70a610a60c5e7c49c783d",
				},
			},
		},
	}, nil
}

// DeployCNativeApp ...
func (r MockedRequester) DeployCNativeApp(
	appCode, appModule, deployEnv string, manifest map[string]any,
) (map[string]any, error) {
	return manifest, nil
}

// GetCNativeAppDeployResult ...
func (r MockedRequester) GetCNativeAppDeployResult(appCode, appModule, deployEnv string) (map[string]any, error) {
	return map[string]any{
		"deployment": map[string]any{
			"deploy_id":            533,
			"status":               "ready",
			"reason":               "AppAvailable",
			"message":              "",
			"last_transition_time": "2023-04-17 10:01:00",
			"operator":             "admin",
			"created":              "2023-04-17 10:00:00",
		},
		"ingress": map[string]any{
			"url": "http://stag-dot-cnative.bkapps.example.com/",
		},
		"conditions": []any{
			map[string]any{
				"type":    "AppAvailable",
				"status":  "True",
				"reason":  "AppAvailable",
				"message": "",
			},
			map[string]any{
				"type":    "AppProgressing",
				"status":  "True",
				"reason":  "NewRevision",
				"message": "",
			},
			map[string]any{
				"type":    "AddOnsProvisioned",
				"status":  "True",
				"reason":  "Provisioned",
				"message": "",
			},
			map[string]any{
				"type":    "HooksFinished",
				"status":  "True",
				"reason":  "Finished",
				"message": "",
			},
		},
		"events": []any{
			map[string]any{
				"name":             "cnative--web-767546656f-2phcm.175aca6b63de0a02",
				"type":             "Normal",
				"reason":           "Killing",
				"count":            "1",
				"message":          "Stopping container web",
				"source_component": "kubelet",
				"first_seen":       "2023-04-17 10:00:01",
				"last_seen":        "2023-04-17 10:00:02",
			},
		},
	}, nil
}

// ListCNativeAppDeployHistory ...
func (r MockedRequester) ListCNativeAppDeployHistory(appCode, appModule, deployEnv string) (map[string]any, error) {
	return map[string]any{
		"count": 2,
		"results": []any{
			map[string]any{
				"id":                   535,
				"operator":             "admin",
				"created":              "2023-04-17 19:44:42",
				"name":                 "cnative-710-1681731882",
				"status":               "ready",
				"last_transition_time": "2023-04-17 19:44:48",
			},
			map[string]any{
				"id":       533,
				"operator": "admin",
				"created":  "2023-04-17 17:05:26",
				"name":     "cnative-708-1681722326",
				"status":   "error",
				"reason":   "Failed",
				"message":  "PreReleaseHook fail to succeed: stat /bin/bash: no such file or directory: unknown",
			},
		},
	}, nil
}

var _ Requester = MockedRequester{}
