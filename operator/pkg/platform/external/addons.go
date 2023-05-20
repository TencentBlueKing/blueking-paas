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

package external

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"

	"github.com/pkg/errors"
	"k8s.io/apimachinery/pkg/util/intstr"
)

// AddonInstance define the structure return from QueryAddonInstance API
type AddonInstance struct {
	// Credentials contains the EnvVar offered by the AddonInstance
	Credentials map[string]intstr.IntOrString `json:"credentials"`
}

// AddonSpecsData ...
type AddonSpecsData struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

// AddonSpecsResult ...
type AddonSpecsResult struct {
	Data []AddonSpecsData `json:"results,omitempty"`
}

// AddonSpecs define specs of the add-on service
type AddonSpecs struct {
	Specs map[string]string `json:"specs,omitempty"`
}

// ToRequestBody convert AddonSpecs to request body
func (s AddonSpecs) ToRequestBody() (io.Reader, error) {
	if len(s.Specs) == 0 {
		return bytes.NewBuffer([]byte{}), nil
	}

	jsonData, err := json.Marshal(s)
	if err != nil {
		return nil, err
	}

	return bytes.NewBuffer(jsonData), nil
}

// ProvisionAddonResult contains the add-on service uuid
type ProvisionAddonResult struct {
	ServiceID string `json:"service_id"`
}

// QueryAddonInstance 调用 bkpaas 对应的接口, 查询应用的增强服务实例
func (c *Client) QueryAddonInstance(
	ctx context.Context,
	appCode, moduleName, environment, addonName string,
) (AddonInstance, error) {
	instance := AddonInstance{}
	path := fmt.Sprintf(
		"/system/bkapps/applications/%s/modules/%s/envs/%s/addons/%s/",
		appCode,
		moduleName,
		environment,
		addonName,
	)

	req, err := c.NewRequest(ctx, "GET", path, bytes.NewBuffer([]byte{}))
	if err != nil {
		return instance, errors.WithStack(err)
	}
	err = c.Do(req).Into(&instance, json.Unmarshal)
	if err != nil {
		return instance, errors.WithStack(err)
	}
	return instance, nil
}

// QueryAddonSpecs 调用 bkpaas 对应的接口, 查询应用的增强服务规格
func (c *Client) QueryAddonSpecs(ctx context.Context, appCode, moduleName, svcID string) (*AddonSpecsResult, error) {
	result := &AddonSpecsResult{}
	path := fmt.Sprintf(
		"/system/bkapps/applications/%s/modules/%s/services/%s/specs",
		appCode,
		moduleName,
		svcID,
	)
	req, err := c.NewRequest(ctx, "GET", path, bytes.NewBuffer([]byte{}))
	if err != nil {
		return nil, errors.WithStack(err)
	}
	err = c.Do(req).Into(result, json.Unmarshal)
	if err != nil {
		return nil, errors.WithStack(err)
	}
	return result, nil
}

// ProvisionAddonInstance 调用 bkpaas 对应接口, 分配应用的增强服务实例
func (c *Client) ProvisionAddonInstance(
	ctx context.Context,
	appCode, moduleName, environment, addonName string, specs AddonSpecs,
) (string, error) {
	path := fmt.Sprintf(
		"/system/bkapps/applications/%s/modules/%s/envs/%s/addons/%s/",
		appCode,
		moduleName,
		environment,
		addonName,
	)

	body, err := specs.ToRequestBody()
	if err != nil {
		return "", errors.WithStack(err)
	}

	req, err := c.NewRequest(ctx, "POST", path, body)
	if err != nil {
		return "", errors.WithStack(err)
	}

	var result ProvisionAddonResult
	err = c.Do(req).Into(&result, json.Unmarshal)
	if err != nil {
		return "", errors.WithStack(err)
	}

	return result.ServiceID, nil
}
