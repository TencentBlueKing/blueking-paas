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

package client

import (
	"context"

	"github.com/pkg/errors"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// stackTraceClient wrap client.Client error with stack
type stackTraceClient struct {
	cli client.Client
}

var _ client.Client = &stackTraceClient{}

// New stackTraceClient
func New(cli client.Client) client.Client {
	return &stackTraceClient{cli: cli}
}

// Scheme returns the scheme this client is using.
func (c *stackTraceClient) Scheme() *runtime.Scheme {
	return c.cli.Scheme()
}

// RESTMapper returns the rest this client is using.
func (c *stackTraceClient) RESTMapper() apimeta.RESTMapper {
	return c.cli.RESTMapper()
}

// Get retrieves an obj for the given object key from the Kubernetes Cluster.
// obj must be a struct pointer so that obj can be updated with the response
// returned by the Server.
func (c *stackTraceClient) Get(ctx context.Context, key client.ObjectKey, obj client.Object) error {
	return errors.WithStack(c.cli.Get(ctx, key, obj))
}

// List retrieves list of objects for a given namespace and list options. On a
// successful call, Items field in the list will be populated with the
// result returned from the server.
func (c *stackTraceClient) List(ctx context.Context, list client.ObjectList, opts ...client.ListOption) error {
	return errors.WithStack(c.cli.List(ctx, list, opts...))
}

// Create saves the object obj in the Kubernetes cluster.
func (c *stackTraceClient) Create(ctx context.Context, obj client.Object, opts ...client.CreateOption) error {
	return errors.WithStack(c.cli.Create(ctx, obj, opts...))
}

// Delete deletes the given obj from Kubernetes cluster.
func (c *stackTraceClient) Delete(ctx context.Context, obj client.Object, opts ...client.DeleteOption) error {
	return errors.WithStack(c.cli.Delete(ctx, obj, opts...))
}

// Update updates the given obj in the Kubernetes cluster. obj must be a
// struct pointer so that obj can be updated with the content returned by the Server.
func (c *stackTraceClient) Update(ctx context.Context, obj client.Object, opts ...client.UpdateOption) error {
	return errors.WithStack(c.cli.Update(ctx, obj, opts...))
}

// Patch patches the given obj in the Kubernetes cluster. obj must be a
// struct pointer so that obj can be updated with the content returned by the Server.
func (c *stackTraceClient) Patch(
	ctx context.Context, obj client.Object, patch client.Patch, opts ...client.PatchOption,
) error {
	return errors.WithStack(c.cli.Patch(ctx, obj, patch, opts...))
}

// DeleteAllOf deletes all objects of the given type matching the given options.
func (c *stackTraceClient) DeleteAllOf(
	ctx context.Context, obj client.Object, opts ...client.DeleteAllOfOption,
) error {
	return errors.WithStack(c.cli.DeleteAllOf(ctx, obj, opts...))
}

// StatusClient knows how to create a client which can update status subresource for kubernetes objects.
func (c *stackTraceClient) Status() client.StatusWriter {
	return &stackTraceStatusWriter{sw: c.cli.Status()}
}

// stackTraceStatusWriter wrap client.StatusWriter error with stack
type stackTraceStatusWriter struct {
	sw client.StatusWriter
}

var _ client.StatusWriter = &stackTraceStatusWriter{}

// Update implements client.StatusWriter.
func (w *stackTraceStatusWriter) Update(ctx context.Context, obj client.Object, opts ...client.UpdateOption) error {
	return errors.WithStack(w.sw.Update(ctx, obj, opts...))
}

// Patch implements client.Client.
func (w *stackTraceStatusWriter) Patch(
	ctx context.Context, obj client.Object, patch client.Patch, opts ...client.PatchOption,
) error {
	return errors.WithStack(w.sw.Patch(ctx, obj, patch, opts...))
}
