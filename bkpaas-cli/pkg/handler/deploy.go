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
	"strings"

	"github.com/TencentBlueKing/gopkg/mapx"
	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/apiresources"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/helper"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/model"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/timex"
)

// NewAppDeployer ...
func NewAppDeployer(appCode string) (Deployer, error) {
	appType := helper.FetchAppType(appCode)
	switch appType {
	case model.AppTypeDefault:
		return DefaultAppDeployer{BaseDeployer{}}, nil
	case model.AppTypeCNative:
		return CNativeAppDeployer{BaseDeployer{}}, nil
	default:
		return nil, errors.Errorf("unsupported app type: '%s'", appType)
	}
}

// BaseDeployer ...
type BaseDeployer struct{}

// GetResult 获取部署结果
func (d BaseDeployer) GetResult(opts model.DeployOptions) (model.DeployResult, error) {
	// 需要根据 deployment_id 查询，因此先从历史记录获取最新记录的 deployment_id
	history, err := d.GetHistory(opts)
	if err != nil {
		return nil, err
	}
	latestRecord := history.Latest()
	if latestRecord == nil {
		return nil, errors.New("no deploy result found")
	}
	// 调用 api 获取部署结果
	respData, err := apiresources.DefaultRequester.GetAppDeployResult(
		opts.AppCode, opts.Module, latestRecord.ID,
	)
	if err != nil {
		return nil, err
	}

	errDetail, _ := respData["error_detail"].(string)
	errTips := []model.ErrTip{}
	for _, tip := range mapx.GetList(respData, "error_tips.helpers") {
		t, _ := tip.(map[string]any)
		errTips = append(errTips, model.ErrTip{Text: t["text"].(string), Link: t["link"].(string)})
	}
	return model.DefaultAppDeployResult{
		AppCode:   opts.AppCode,
		Module:    opts.Module,
		DeployEnv: opts.DeployEnv,
		DeployID:  latestRecord.ID,
		Status:    mapx.GetStr(respData, "status"),
		Logs:      mapx.GetStr(respData, "logs"),
		ErrDetail: errDetail,
		ErrTips:   errTips,
	}, nil
}

// GetHistory 获取部署历史
func (d BaseDeployer) GetHistory(opts model.DeployOptions) (model.DeployHistory, error) {
	respData, err := apiresources.DefaultRequester.ListAppDeployHistory(opts.AppCode, opts.Module, opts.DeployEnv)
	if err != nil {
		return nil, err
	}
	records := []model.AppDeployRecord{}
	for _, deploy := range mapx.GetList(respData, "results") {
		dp, _ := deploy.(map[string]any)

		environment := mapx.GetStr(dp, "environment")
		// 如果已指定部署环境，需要进行检查过滤不属于该环境的记录
		if opts.DeployEnv != "" && environment != opts.DeployEnv {
			continue
		}
		revision := mapx.GetStr(dp, "repo.revision")
		startTime, _ := dp["start_time"].(string)
		endTime, _ := dp["complete_time"].(string)

		records = append(records, model.AppDeployRecord{
			ID:       mapx.GetStr(dp, "id"),
			Branch:   mapx.GetStr(dp, "repo.name"),
			Version:  revision[:min(ShortRevisionLength, len(revision))],
			Operator: mapx.GetStr(dp, "operator.username"),
			CostTime: timex.CalcDuration(startTime, endTime),
			Status:   mapx.GetStr(dp, "status"),
			StartAt:  mapx.GetStr(dp, "created"),
		})
	}
	return model.DefaultAppDeployHistory{
		AppCode:   opts.AppCode,
		Module:    opts.Module,
		DeployEnv: opts.DeployEnv,
		Total:     cast.ToInt(respData["count"]),
		Records:   records,
	}, nil
}

// DefaultAppDeployer 普通应用部署器
type DefaultAppDeployer struct {
	BaseDeployer
}

// Deploy 执行部署操作
func (d DefaultAppDeployer) Deploy(opts model.DeployOptions) error {
	data := map[string]any{"version_type": "branch", "version_name": opts.Branch}
	_, err := apiresources.DefaultRequester.DeployApp(
		opts.AppCode, opts.Module, opts.DeployEnv, data,
	)
	return err
}

var _ Deployer = DefaultAppDeployer{}

// CNativeAppDeployer 云原生应用部署器
type CNativeAppDeployer struct {
	BaseDeployer
}

// Deploy 执行部署操作
func (d CNativeAppDeployer) Deploy(opts model.DeployOptions) error {
	appCode, appModule, deployEnv := opts.AppCode, opts.Module, opts.DeployEnv
	manifest, tag, branch := opts.BkAppManifest, opts.Tag, opts.Branch
	if manifest != nil {
		// 导入 manifest
		_, err := apiresources.DefaultRequester.UpdateBkAppModel(appCode, appModule, manifest)
		if err != nil {
			return err
		}
		if tag == "" {
			tag = "latest"
		}
		// 从 manifest 中提取 image 信息
		image := mapx.GetStr(manifest, "spec.build.image")
		// 从 image 中提取 tag 信息
		if pos := strings.LastIndex(image, ":"); pos != -1 {
			tag = image[pos+1:]
		}
	}
	var data map[string]any
	if manifest != nil || tag != "" {
		data = map[string]any{"version_type": "image", "version_name": tag}
	} else if branch != "" {
		data = map[string]any{"version_type": "branch", "version_name": branch}
	} else {
		return errors.New("branch or manifest or tag is required")
	}
	_, err := apiresources.DefaultRequester.DeployApp(
		appCode, appModule, deployEnv, data,
	)
	return err
}

var _ Deployer = CNativeAppDeployer{}
