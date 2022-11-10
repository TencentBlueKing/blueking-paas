/*
 * Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
 * Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * 	http://opensource.org/licenses/MIT
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

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
)

// WithAppInfoAnnotations will set a fake app info to bkapp.annotations
func WithAppInfoAnnotations(bkapp *paasv1alpha1.BkApp) *paasv1alpha1.BkApp {
	annotations := bkapp.GetAnnotations()
	annotations[paasv1alpha1.BkAppRegionKey] = "region"
	annotations[paasv1alpha1.BkAppCodeKey] = "app-code"
	annotations[paasv1alpha1.BkAppNameKey] = "app-name"
	annotations[paasv1alpha1.ModuleNameKey] = "module"
	annotations[paasv1alpha1.EnvironmentKey] = "stag"
	annotations[paasv1alpha1.EngineAppNameKey] = "bkapp-app-code-stag"
	return bkapp
}

// WithAddons will set the addons keys to bkapp.annotations
func WithAddons(bkapp *paasv1alpha1.BkApp, addons ...string) *paasv1alpha1.BkApp {
	var data []byte
	var err error
	if data, err = json.Marshal(addons); err != nil {
		panic(err)
	}

	annotations := bkapp.GetAnnotations()
	annotations[paasv1alpha1.AddonsAnnoKey] = string(data)
	return bkapp
}

// WithPhase will set the Status.Phase field
func WithPhase(bkapp *paasv1alpha1.BkApp, phase paasv1alpha1.AppPhase) *paasv1alpha1.BkApp {
	bkapp.Status.Phase = phase
	return bkapp
}
