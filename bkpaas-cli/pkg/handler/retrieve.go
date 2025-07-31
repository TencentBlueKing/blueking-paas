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

package handler

import (
	"github.com/TencentBlueKing/gopkg/mapx"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/apiresources"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/model"
)

// BasicInfoRetriever 应用基础信息查看
type BasicInfoRetriever struct{}

// NewBasicInfoRetriever ...
func NewBasicInfoRetriever() *BasicInfoRetriever {
	return &BasicInfoRetriever{}
}

// Exec 调用 API 获取应用基础信息
func (v *BasicInfoRetriever) Exec(appCode string) (model.AppInfo, error) {
	appInfo, err := apiresources.DefaultRequester.GetAppInfo(appCode)
	if err != nil {
		return nil, err
	}

	modules := []model.ModuleBasicInfo{}
	for _, mod := range mapx.GetList(appInfo, "application.modules") {
		m, _ := mod.(map[string]any)

		// 环境基础信息
		envs := []model.EnvBasicInfo{}
		for envName, clusterInfo := range mapx.GetMap(m, "clusters") {
			cluster := mapx.GetStr(clusterInfo.(map[string]any), "name")
			if clusterID := mapx.GetStr(clusterInfo.(map[string]any), "bcs_cluster_id"); clusterID != "" {
				cluster += " -> " + clusterID
			}
			envs = append(envs, model.EnvBasicInfo{Name: envName, Cluster: cluster})
		}

		// 兼容 RepoUrl 可能为 nil 的情况
		repoUrl := mapx.Get(m, "repo.repo_url", "")
		if repoUrl == nil {
			repoUrl = ""
		}

		// 模块基础信息
		modules = append(modules, model.ModuleBasicInfo{
			Name:     mapx.GetStr(m, "name"),
			RepoType: mapx.GetStr(m, "repo.display_name"),
			RepoURL:  repoUrl.(string),
			Envs:     envs,
		})
	}

	return model.AppBasicInfo{
		Code:    appCode,
		Name:    mapx.GetStr(appInfo, "application.name"),
		Region:  mapx.GetStr(appInfo, "application.region_name"),
		AppType: mapx.GetStr(appInfo, "application.type"),
		Modules: modules,
	}, nil
}

var _ Retriever = &BasicInfoRetriever{}
