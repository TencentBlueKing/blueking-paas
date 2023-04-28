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

package testing

import (
	"encoding/json"

	"bk.tencent.com/paas-app-operator/api/v1alpha2"
)

// WithAppInfoAnnotations will set a fake app info to bkapp.annotations
func WithAppInfoAnnotations(bkapp *v1alpha2.BkApp) *v1alpha2.BkApp {
	annotations := bkapp.GetAnnotations()
	annotations[v1alpha2.BkAppRegionKey] = "region"
	annotations[v1alpha2.BkAppCodeKey] = "app-code"
	annotations[v1alpha2.BkAppNameKey] = "app-name"
	annotations[v1alpha2.ModuleNameKey] = "module"
	annotations[v1alpha2.EnvironmentKey] = "stag"
	annotations[v1alpha2.EngineAppNameKey] = "bkapp-app-code-stag"
	return bkapp
}

// WithAddons will set the addons keys to bkapp.annotations
func WithAddons(bkapp *v1alpha2.BkApp, addons ...string) *v1alpha2.BkApp {
	var data []byte
	var err error
	if data, err = json.Marshal(addons); err != nil {
		panic(err)
	}

	annotations := bkapp.GetAnnotations()
	annotations[v1alpha2.AddonsAnnoKey] = string(data)
	return bkapp
}
