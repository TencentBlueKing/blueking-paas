package testing

// Config for testing
type Config struct{}

// GetMaxProcesses for testing
func (c Config) GetMaxProcesses() int32 {
	return 8
}

// GetProcMaxReplicas for testing
func (c Config) GetProcMaxReplicas() int32 {
	return 5
}

// GetProcDefaultCpuLimit for testing
func (c Config) GetProcDefaultCpuLimit() string {
	return "4"
}

// GetProcDefaultMemLimit for testing
func (c Config) GetProcDefaultMemLimit() string {
	return "1Gi"
}

// GetProcDefaultCpuRequest for testing
func (c Config) GetProcDefaultCpuRequest() string {
	return ""
}

// GetProcDefaultMemRequest for testing
func (c Config) GetProcDefaultMemRequest() string {
	return ""
}

// GetIngressClassName for testing
func (c Config) GetIngressClassName() string {
	return "test-nginx"
}

// GetCustomDomainIngressClassName for testing
func (c Config) GetCustomDomainIngressClassName() string {
	return "test-custom-domain-nginx"
}

// IsAutoscalingEnabled for testing
func (c Config) IsAutoscalingEnabled() bool {
	return false
}
