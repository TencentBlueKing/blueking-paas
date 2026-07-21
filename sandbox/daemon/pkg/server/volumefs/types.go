package volumefs

// ListRequest 列目录请求(GET /files/list)。base_path 由 apiserver 下发(jail 根), rel_path 为 volume 内相对路径。
type ListRequest struct {
	BasePath  string `form:"base_path" validate:"required"`
	RelPath   string `form:"rel_path" validate:"optional"`
	Recursive bool   `form:"is_recursive" validate:"optional"`
	Since     string `form:"since" validate:"optional"`
	Until     string `form:"until" validate:"optional"`
	Page      int    `form:"page" validate:"optional"`
	PageSize  int    `form:"page_size" validate:"optional"`
}

// FileItem 列表/元数据中的单个文件条目。Path 为相对 jail 根(volume 根)的路径。
type FileItem struct {
	Path       string `json:"path"`
	Name       string `json:"name"`
	IsDir      bool   `json:"is_dir"`
	Size       int64  `json:"size"`
	ModifiedAt string `json:"modified_at"`
	Mime       string `json:"mime"`
}

// ListExtraData 汇总过滤后结果中的文件和目录数量。
type ListExtraData struct {
	Files       int `json:"files"`
	Directories int `json:"directory"`
}

// ListResponse 列目录响应(分页在 daemon 侧完成)。
// {count, results, extra_data} 与 apiserver 列表响应风格保持一致, 由 apiserver 直接透传给前端。
type ListResponse struct {
	Count     int           `json:"count"`
	Results   []FileItem    `json:"results"`
	ExtraData ListExtraData `json:"extra_data"`
}

// StatRequest 元数据请求(GET /files/stat)。文件不存在时 Exists=false, 仍返回 200。
type StatRequest struct {
	BasePath string `form:"base_path" validate:"required"`
	RelPath  string `form:"rel_path" validate:"required"`
}

type StatResponse struct {
	Exists     bool   `json:"exists"`
	Path       string `json:"path"`
	Size       int64  `json:"size"`
	ModifiedAt string `json:"modified_at"`
	Mime       string `json:"mime"`
}

// PreviewRequest 文本预览请求(GET /files/preview)。max_bytes<=0 或超限时用 previewMaxBytes。
type PreviewRequest struct {
	BasePath string `form:"base_path" validate:"required"`
	RelPath  string `form:"rel_path" validate:"required"`
	MaxBytes int64  `form:"max_bytes" validate:"optional"`
}

// ExportFileRequest 导出文件请求(POST /files/export): 读取 volume 文件并上传到 UploadURL。
type ExportFileRequest struct {
	BasePath  string `json:"base_path" validate:"required"`
	RelPath   string `json:"rel_path" validate:"required"`
	UploadURL string `json:"upload_url" validate:"required"`
}

// ExportFileResponse 导出结果。Mtime 为导出时文件的修改时间(RFC3339 UTC)。
type ExportFileResponse struct {
	Sha256 string `json:"sha256"`
	Size   int64  `json:"size"`
	Mtime  string `json:"mtime"`
}

// DeleteResponse 删除响应(删除不存在的文件视为成功, 幂等)。
type DeleteResponse struct {
	Deleted bool `json:"deleted"`
}
