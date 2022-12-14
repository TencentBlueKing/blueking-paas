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

	"github.com/pkg/errors"
)

// AddonInstance define the structure return from QueryAddonInstance API
type AddonInstance struct {
	// Credentials contains the EnvVar offered by the AddonInstance
	Credentials map[string]string `json:"credentials"`
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

// ProvisionAddonInstance 调用 bkpaas 对应接口, 分配应用的增强服务实例
func (c *Client) ProvisionAddonInstance(
	ctx context.Context,
	appCode, moduleName, environment, addonName string,
) error {
	path := fmt.Sprintf(
		"/system/bkapps/applications/%s/modules/%s/envs/%s/addons/%s/",
		appCode,
		moduleName,
		environment,
		addonName,
	)

	req, err := c.NewRequest(ctx, "POST", path, bytes.NewBuffer([]byte{}))
	if err != nil {
		return errors.WithStack(err)
	}

	return errors.WithStack(c.Do(req).err)
}
