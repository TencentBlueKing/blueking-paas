package v1alpha1

import (
	"encoding/json"

	"github.com/jinzhu/copier"
	corev1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/conversion"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/utils/kubetypes"
)

var _ conversion.Convertible = &BkApp{}

// ConvertTo converts this BkApp to the Hub version (v1alpha2).
func (src *BkApp) ConvertTo(dstRaw conversion.Hub) error {
	dst := dstRaw.(*paasv1alpha2.BkApp)

	err := copier.CopyWithOption(
		&dst.ObjectMeta,
		&src.ObjectMeta,
		copier.Option{DeepCopy: true},
	)
	if err != nil {
		return err
	}

	// Handle Processes field
	legacyProcImageConfig := make(paasv1alpha2.LegacyProcConfig)
	legacyProcResConfig := make(paasv1alpha2.LegacyProcConfig)
	for _, proc := range src.Spec.Processes {
		dstProc := paasv1alpha2.Process{
			Name:         proc.Name,
			Replicas:     proc.Replicas,
			ResQuotaPlan: proc.ResQuotaPlan,
			Command:      proc.Command,
			Args:         proc.Args,
			TargetPort:   proc.TargetPort,
		}
		if proc.Image != "" {
			legacyProcImageConfig[proc.Name] = map[string]string{
				"image":  proc.Image,
				"policy": string(proc.ImagePullPolicy),
			}
		}
		if proc.CPU != "" && proc.Memory != "" {
			legacyProcResConfig[proc.Name] = map[string]string{
				"cpu":    proc.CPU,
				"memory": proc.Memory,
			}
		}

		// Append to the destination process list
		dst.Spec.Processes = append(dst.Spec.Processes, dstProc)
	}

	// Save legacy proc image and resource configs to annotations
	if err = kubetypes.SetJsonAnnotation(dst, LegacyProcImageAnnoKey, legacyProcImageConfig); err != nil {
		return err
	}
	if err = kubetypes.SetJsonAnnotation(dst, LegacyProcResAnnoKey, legacyProcResConfig); err != nil {
		return err
	}

	// convert Addons from "bkapp.paas.bk.tencent.com/addons" annotation to Spec.Addons
	addons, err := src.ExtractAddons()
	if err != nil {
		return err
	}

	tempAddons := make([]paasv1alpha2.Addon, 0)
	if src.Spec.Addons != nil {
		_ = copier.CopyWithOption(
			&tempAddons,
			&src.Spec.Addons,
			copier.Option{IgnoreEmpty: true, DeepCopy: true},
		)
	}
	specMap := make(map[string][]paasv1alpha2.AddonSpec)
	for _, addon := range tempAddons {
		specMap[addon.Name] = addon.Specs
	}
	for _, addonName := range addons {
		dst.Spec.Addons = append(dst.Spec.Addons, paasv1alpha2.Addon{
			Name:  addonName,
			Specs: specMap[addonName],
		})
	}
	// remove "bkapp.paas.bk.tencent.com/addons" annotation
	delete(dst.Annotations, AddonsAnnoKey)

	// Handle fields that are using identical structures
	_ = copier.CopyWithOption(
		&dst.Spec.Configuration,
		&src.Spec.Configuration,
		copier.Option{IgnoreEmpty: true, DeepCopy: true},
	)
	_ = copier.CopyWithOption(
		&dst.Spec.Build,
		&src.Spec.Build,
		copier.Option{IgnoreEmpty: true, DeepCopy: true},
	)

	// Copy Hooks field, extra logics needs because of the pointer type
	if src.Spec.Hooks == nil {
		dst.Spec.Hooks = nil
	} else {
		dst.Spec.Hooks = &paasv1alpha2.AppHooks{}
		_ = copier.CopyWithOption(
			&dst.Spec.Hooks,
			&src.Spec.Hooks,
			copier.Option{IgnoreEmpty: true, DeepCopy: true},
		)
	}

	// Copy EnvOverlay field, extra logics needs because of the pointer type
	if src.Spec.EnvOverlay == nil {
		dst.Spec.EnvOverlay = nil
	} else {
		dst.Spec.EnvOverlay = &paasv1alpha2.AppEnvOverlay{}
		_ = copier.CopyWithOption(
			&dst.Spec.EnvOverlay,
			&src.Spec.EnvOverlay,
			copier.Option{IgnoreEmpty: true, DeepCopy: true},
		)
	}

	// Copy Status field
	_ = copier.CopyWithOption(
		&dst.Status, &src.Status, copier.Option{IgnoreEmpty: true, DeepCopy: true},
	)

	return nil
}

// ConvertFrom converts from the Hub version (v1alpha2) to this version.
func (dst *BkApp) ConvertFrom(srcRaw conversion.Hub) error {
	src := srcRaw.(*paasv1alpha2.BkApp)

	err := copier.CopyWithOption(
		&dst.ObjectMeta,
		&src.ObjectMeta,
		copier.Option{DeepCopy: true},
	)
	if err != nil {
		return err
	}

	// Handle Processes field
	legacyProcImageConfig, _ := kubetypes.GetJsonAnnotation[paasv1alpha2.LegacyProcConfig](src, LegacyProcImageAnnoKey)
	legacyProcResConfig, _ := kubetypes.GetJsonAnnotation[paasv1alpha2.LegacyProcConfig](src, LegacyProcResAnnoKey)
	for _, proc := range src.Spec.Processes {
		dstProc := Process{
			Name:         proc.Name,
			Replicas:     proc.Replicas,
			ResQuotaPlan: proc.ResQuotaPlan,
			Command:      proc.Command,
			Args:         proc.Args,
			TargetPort:   proc.TargetPort,

			// Legacy fields
			Image:           legacyProcImageConfig[proc.Name]["image"],
			ImagePullPolicy: corev1.PullPolicy(legacyProcImageConfig[proc.Name]["policy"]),
			CPU:             legacyProcResConfig[proc.Name]["cpu"],
			Memory:          legacyProcResConfig[proc.Name]["memory"],
		}
		// Append to the destination process list
		dst.Spec.Processes = append(dst.Spec.Processes, dstProc)
	}

	// Handle fields that are using identical structures
	_ = copier.CopyWithOption(
		&dst.Spec.Configuration,
		&src.Spec.Configuration,
		copier.Option{IgnoreEmpty: true, DeepCopy: true},
	)
	_ = copier.CopyWithOption(
		&dst.Spec.Build,
		&src.Spec.Build,
		copier.Option{IgnoreEmpty: true, DeepCopy: true},
	)

	dst.Annotations = make(map[string]string)
	if src.Annotations != nil {
		_ = copier.CopyWithOption(
			&dst.Annotations,
			&src.Annotations,
			copier.Option{IgnoreEmpty: true, DeepCopy: true},
		)
	}
	if src.Spec.Addons != nil {
		dst.Spec.Addons = make([]Addon, 0)
		_ = copier.CopyWithOption(
			&dst.Spec.Addons,
			&src.Spec.Addons,
			copier.Option{IgnoreEmpty: true, DeepCopy: true},
		)

		addonNames := make([]string, 0)
		for _, addon := range dst.Spec.Addons {
			addonNames = append(addonNames, addon.Name)
		}
		addonAnnotation, err := json.Marshal(addonNames)
		if err != nil {
			return err
		}
		dst.Annotations[AddonsAnnoKey] = string(addonAnnotation)
	}

	// Copy Hooks field, extra logics needs because of the pointer type
	if src.Spec.Hooks == nil {
		dst.Spec.Hooks = nil
	} else {
		dst.Spec.Hooks = &AppHooks{}
		_ = copier.CopyWithOption(
			&dst.Spec.Hooks,
			&src.Spec.Hooks,
			copier.Option{IgnoreEmpty: true, DeepCopy: true},
		)
	}

	// Copy EnvOverlay field
	if src.Spec.EnvOverlay == nil {
		dst.Spec.EnvOverlay = nil
	} else {
		dst.Spec.EnvOverlay = &AppEnvOverlay{}
		_ = copier.CopyWithOption(
			&dst.Spec.EnvOverlay,
			&src.Spec.EnvOverlay,
			copier.Option{IgnoreEmpty: true, DeepCopy: true},
		)
	}

	// Copy Status field
	_ = copier.CopyWithOption(
		&dst.Status, &src.Status, copier.Option{IgnoreEmpty: true, DeepCopy: true},
	)

	return nil
}
