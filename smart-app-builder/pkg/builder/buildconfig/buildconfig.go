package buildconfig

// ModuleBuildConfig 模块构建配置
type ModuleBuildConfig struct {
	SourceDir  string
	ModuleName string
	Buildpacks []Buildpack
	Envs       map[string]string
}

// BuildConfig is the configuration related with application building
type BuildConfig struct {
	Buildpacks []Buildpack `yaml:"buildpacks"`
}
