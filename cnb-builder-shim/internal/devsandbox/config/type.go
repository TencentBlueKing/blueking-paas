package config

// 源码获取方式
const (
	HTTP   = "HTTP"
	BKREPO = "BKREPO"
	GIT    = "GIT"
)

// SourceConfig 源码配置
type SourceConfig struct {
	// 源码获取方式
	SourceFetchMethod string
	// 源码地址
	SourceGetUrl string
	// Git 仓库版本
	GitRevision string
	// 上传路径
	UploadDir string
}

// Config  构建配置
type Config struct {
	// 源码配置
	Source SourceConfig
	// ...
}
