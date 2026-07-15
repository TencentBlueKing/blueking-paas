package pv

// ListRequest 列目录请求。base_path 由 apiserver 下发(jail 根), rel_path 为 volume 内相对路径。
type ListRequest struct {
	BasePath  string `json:"base_path" validate:"required"`
	RelPath   string `json:"rel_path,omitempty" validate:"optional"`
	Recursive bool   `json:"recursive,omitempty" validate:"optional"`
	Page      int    `json:"page,omitempty" validate:"optional"`
	PageSize  int    `json:"page_size,omitempty" validate:"optional"`
}

// FileItem 列表 / 元数据中的单个文件条目。
type FileItem struct {
	// Path 相对 jail 根(即 volume 根)的路径
	Path       string `json:"path"`
	Name       string `json:"name"`
	IsDir      bool   `json:"is_dir"`
	Size       int64  `json:"size"`
	ModifiedAt string `json:"modified_at"`
	Mime       string `json:"mime"`
	// Sha256 恒为 nil, 去重表缓存值由 apiserver 回填
	Sha256 *string `json:"sha256"`
}

// ListResponse 列目录响应。分页在 daemon 侧完成。
type ListResponse struct {
	Total int        `json:"total"`
	Items []FileItem `json:"items"`
}

// StatRequest 元数据请求。
type StatRequest struct {
	BasePath string `json:"base_path" validate:"required"`
	RelPath  string `json:"rel_path" validate:"required"`
}

// StatResponse 元数据响应。文件不存在时 Exists=false, 仍返回 HTTP 200。
type StatResponse struct {
	Exists     bool   `json:"exists"`
	Path       string `json:"path"`
	Size       int64  `json:"size"`
	ModifiedAt string `json:"modified_at"`
	Mime       string `json:"mime"`
}

// PreviewRequest 文本预览请求。
type PreviewRequest struct {
	BasePath string `json:"base_path" validate:"required"`
	RelPath  string `json:"rel_path" validate:"required"`
	// MaxBytes 截断上限, <=0 时使用 config.G.PreviewMaxBytes
	MaxBytes int64 `json:"max_bytes,omitempty" validate:"optional"`
}

// ArchiveRequest 归档请求。daemon 读文件算 sha256 并 PUT 到 apiserver 下发的临时 UploadURL。
type ArchiveRequest struct {
	BasePath  string `json:"base_path" validate:"required"`
	RelPath   string `json:"rel_path" validate:"required"`
	UploadURL string `json:"upload_url" validate:"required"`
}

// ArchiveResponse 归档结果。
type ArchiveResponse struct {
	Sha256 string `json:"sha256"`
	Size   int64  `json:"size"`
	// Mtime 归档时文件的修改时间(RFC3339, UTC)
	Mtime string `json:"mtime"`
}

// DeleteResponse 删除响应。删除不存在的文件视为成功(幂等)。
type DeleteResponse struct {
	Deleted bool `json:"deleted"`
}
