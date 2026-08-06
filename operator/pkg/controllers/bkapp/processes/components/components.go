/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
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

package components

import (
	"bytes"
	"encoding/json"
	"text/template"

	"github.com/pkg/errors"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/util/strategicpatch"
	"sigs.k8s.io/yaml"

	sandboxv1beta1 "bk.tencent.com/paas-app-operator/api/sandbox/v1beta1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	components "bk.tencent.com/paas-app-operator/pkg/components/manager"
	appsv1 "k8s.io/api/apps/v1"
)

// ComponentMutator inject component to deployment
type ComponentMutator struct {
	component     paasv1alpha2.Component
	defaultParams map[string]any
}

// patchTo inject component to object via a strategic merge
// patch.
func patchTo[T any](c *ComponentMutator, obj *T) error {
	patchBytes, err := c.getTemplate()
	if err != nil {
		return errors.Wrapf(err, "get template %s:%s", c.component.Name, c.component.Version)
	}
	originalBytes, err := json.Marshal(obj)
	if err != nil {
		return errors.Wrap(err, "json marshal object")
	}
	patchJSONBytes, err := yaml.YAMLToJSON(patchBytes)
	if err != nil {
		return errors.Wrap(err, "component tpl yaml to json")
	}
	var dataStruct T
	patchedBytes, err := strategicpatch.StrategicMergePatch(originalBytes, patchJSONBytes, dataStruct)
	if err != nil {
		return errors.Wrap(err, "strategic merge patch")
	}
	patched := new(T)
	if err = json.Unmarshal(patchedBytes, patched); err != nil {
		return errors.Wrap(err, "json unmarshal patched object")
	}
	*obj = *patched
	return nil
}

// getTemplate get component template from configmap
func (c *ComponentMutator) getTemplate() ([]byte, error) {
	manager, err := components.NewComponentLoader()
	if err != nil {
		return nil, err
	}
	tpl, err := manager.GetTemplate(c.component.Name, c.component.Version)
	if err != nil {
		return nil, err
	}
	// 渲染模板
	tplBytes, err := c.renderTemplate(string(tpl))
	if err != nil {
		return nil, errors.Wrap(err, "render component template")
	}
	return tplBytes, nil
}

// renderTemplate render component template using params
func (c *ComponentMutator) renderTemplate(templateContent string) ([]byte, error) {
	tmpl, err := template.New("component").Parse(templateContent)
	if err != nil {
		return nil, err
	}

	paramValues := make(map[string]any)
	for k, v := range c.defaultParams {
		paramValues[k] = v
	}

	if len(c.component.Properties.Raw) > 0 {
		if err = json.Unmarshal(c.component.Properties.Raw, &paramValues); err != nil {
			return nil, err
		}
	}

	var buf bytes.Buffer
	if err = tmpl.Execute(&buf, paramValues); err != nil {
		return nil, err
	}

	return buf.Bytes(), nil
}

// PatchToDeployment patch all components to deployment
func PatchToDeployment(
	proc *paasv1alpha2.Process,
	deployment *appsv1.Deployment,
) error {
	for _, component := range proc.Components {
		mutator := &ComponentMutator{
			component: component,
			defaultParams: map[string]any{
				"procName": proc.Name,
			},
		}
		err := patchTo(mutator, deployment)
		if err != nil {
			return err
		}
	}
	return nil
}

// PatchToSandboxInstance patches all of the process's components onto a
// SandboxInstance CR.
//
// Note that a strategic merge patch does not preserve list order, so the main
// container may end up behind the injected sidecars. Containers are looked up by
// name rather than by position, so the resulting order carries no meaning.
//
// VolumeClaimTemplates are merged by metadata.name after each patch: a PVC's
// name lives under metadata, so struct-tag strategic merge cannot use
// patchMergeKey:"name" the way StatefulSetSpec does with its OpenAPI schema.
func PatchToSandboxInstance(
	proc *paasv1alpha2.Process,
	sbi *sandboxv1beta1.SandboxInstance,
) error {
	for _, component := range proc.Components {
		priorClaims := sbi.Spec.VolumeClaimTemplates
		mutator := &ComponentMutator{
			component: component,
			defaultParams: map[string]any{
				"procName": proc.Name,
				// Components that declare namespace-scoped resources (such as the PVC
				// templates of persistent_rootfs) must derive unique names from the
				// workload, because several processes of the same application share a
				// namespace. sbi.Name is already names.Workload(bkapp, proc).
				"workloadName": sbi.Name,
			},
		}
		if err := patchTo(mutator, sbi); err != nil {
			return err
		}
		sbi.Spec.VolumeClaimTemplates = mergeVolumeClaimTemplates(priorClaims, sbi.Spec.VolumeClaimTemplates)
	}
	return nil
}

// mergeVolumeClaimTemplates upserts patched into base by metadata.name. Entries
// that appear only in patched are appended; a name present in both keeps the
// patched copy.
func mergeVolumeClaimTemplates(base, patched []corev1.PersistentVolumeClaim) []corev1.PersistentVolumeClaim {
	if len(patched) == 0 {
		return base
	}
	if len(base) == 0 {
		return patched
	}
	merged := make([]corev1.PersistentVolumeClaim, len(base))
	copy(merged, base)
	index := make(map[string]int, len(merged))
	for i, claim := range merged {
		index[claim.Name] = i
	}
	// 同名用 patch 覆盖，新的直接追加
	for _, claim := range patched {
		if i, ok := index[claim.Name]; ok {
			merged[i] = claim
			continue
		}
		index[claim.Name] = len(merged)
		merged = append(merged, claim)
	}
	return merged
}
