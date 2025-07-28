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
	"github.com/spf13/cast"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/apiresources"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/model"
)

// AppLister ...
type AppLister struct{}

// NewAppLister ...
func NewAppLister() *AppLister {
	return &AppLister{}
}

// Exec 获取应用列表
func (a AppLister) Exec() (model.Items, error) {
	ret, err := apiresources.DefaultRequester.ListAppMinimal()
	if err != nil {
		return nil, err
	}

	applications := []model.AppBasicInfo{}
	for _, item := range mapx.GetList(ret, "results") {
		applications = append(applications, model.AppBasicInfo{
			Code: mapx.GetStr(item.(map[string]any), "application.code"),
			Name: mapx.GetStr(item.(map[string]any), "application.name"),
		})
	}
	return model.MinimalApplications{Total: cast.ToInt(ret["count"]), Apps: applications}, nil
}

var _ Lister = AppLister{}
