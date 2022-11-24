/*
 * Tencent is pleased to support the open source community by making
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

package dgroupmapping

import (
	"context"
	"fmt"

	"github.com/samber/lo"
	networkingv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/controllers/reconcilers"
	res "bk.tencent.com/paas-app-operator/pkg/controllers/resources"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/labels"
)

// DGroupMappingSyncer sync ingress resources for DomainGroupMapping objs.
// In order to use this type, the mapping object must reference to a valid BkApp.
type DGroupMappingSyncer struct {
	Client client.Client
	BkApp  *v1alpha1.BkApp
}

// NewDGroupMappingSyncer creates a DGroupMappingSyncer object
// - bkapp is the owner for current syncer, usually is the referenced BkApp object
//   of DomainGroupMapping object.
func NewDGroupMappingSyncer(
	client client.Client,
	bkapp *v1alpha1.BkApp,
) *DGroupMappingSyncer {
	return &DGroupMappingSyncer{Client: client, BkApp: bkapp}
}

// Sync is the main method for syncing resources, it returns the expected domain
// groups if the sync procedure finished successfully.
func (r *DGroupMappingSyncer) Sync(
	ctx context.Context,
	dgmapping *v1alpha1.DomainGroupMapping,
) ([]res.DomainGroup, error) {
	// Sync ingress resources
	current, err := r.ListCurrentIngresses(ctx, dgmapping)
	if err != nil {
		return nil, err
	}
	domains := res.MappingToDomainGroups(dgmapping)
	expected, err := r.getWantedIngresses(dgmapping, domains)
	if err != nil {
		return nil, err
	}

	// Delete outdated resources
	outdated := reconcilers.FindExtraByName(current, expected)
	if len(outdated) != 0 {
		for _, ingress := range outdated {
			if err := r.Client.Delete(ctx, ingress); err != nil {
				return nil, err
			}
		}
	}
	// Update or create ingress resources
	for _, ingress := range expected {
		if err := r.applyIngress(ctx, ingress); err != nil {
			return nil, err
		}
	}
	return domains, nil
}

// ListCurrentIngresses lists ingress resources related with current mapping object
func (r *DGroupMappingSyncer) ListCurrentIngresses(
	ctx context.Context,
	dgmapping *v1alpha1.DomainGroupMapping,
) (results []*networkingv1.Ingress, err error) {
	current := networkingv1.IngressList{}
	err = r.Client.List(
		ctx,
		&current,
		client.InNamespace(r.BkApp.GetNamespace()),
		client.MatchingLabels(labels.MappingIngress(dgmapping)),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to list ingresses: %w", err)
	}
	return lo.ToSlicePtr(current.Items), nil
}

// getWantedIngresses get the desired ingress resources
func (r *DGroupMappingSyncer) getWantedIngresses(
	dgmapping *v1alpha1.DomainGroupMapping,
	domains []res.DomainGroup,
) ([]*networkingv1.Ingress, error) {
	var results []*networkingv1.Ingress
	for _, group := range domains {
		builder, err := res.NewIngressBuilder(group.SourceType, r.BkApp)
		if err != nil {
			return nil, fmt.Errorf("fail to create builder: %w", err)
		}
		ings, err := builder.Build(group.Domains)
		if err != nil {
			return nil, fmt.Errorf("fail to generate ingresses: %w", err)
		}
		results = append(results, ings...)
	}
	setLabelsAndOwner(results, dgmapping)
	return results, nil
}

// applyIngress creates or update an Ingress object
func (r *DGroupMappingSyncer) applyIngress(ctx context.Context, ingress *networkingv1.Ingress) error {
	return reconcilers.UpsertObject(ctx, r.Client, ingress, nil)
}

// Set the labels and owner fields for a slice of ingresses
func setLabelsAndOwner(ings []*networkingv1.Ingress, dgmapping *paasv1alpha1.DomainGroupMapping) {
	for _, ingress := range ings {
		ingress.Labels = lo.Assign(ingress.Labels, labels.MappingIngress(dgmapping))
		ingress.OwnerReferences = []metav1.OwnerReference{
			*metav1.NewControllerRef(dgmapping, schema.GroupVersionKind{
				Group:   paasv1alpha1.GroupVersion.Group,
				Version: paasv1alpha1.GroupVersion.Version,
				Kind:    paasv1alpha1.KindDomainGroupMapping,
			}),
		}
	}
}

// DeleteIngresses delete all related ingresses of given DomainGroupMapping
func DeleteIngresses(ctx context.Context, c client.Client, dgmapping *v1alpha1.DomainGroupMapping) error {
	opts := []client.DeleteAllOfOption{
		client.InNamespace(dgmapping.GetNamespace()),
		client.MatchingLabels(labels.MappingIngress(dgmapping)),
	}
	return c.DeleteAllOf(ctx, &networkingv1.Ingress{}, opts...)
}
