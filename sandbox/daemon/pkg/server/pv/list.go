package pv

import (
	"io/fs"
	"os"
	"path/filepath"
	"sort"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

const (
	// defaultPageSize 默认分页大小
	defaultPageSize = 100
	// maxPageSize 分页大小上限, 超出 clamp 到此值
	maxPageSize = 500
)

// ListFiles godoc
//
//	@Summary		List files in a volume path
//	@Description	List files under base_path/rel_path with pagination, optionally recursive
//	@Tags			pv
//	@Accept			json
//	@Produce		json
//	@Param			request	body		ListRequest	true	"List request"
//	@Success		200		{object}	ListResponse
//	@Router			/files/list [post]
//
//	@id				ListFiles
func ListFiles(c *gin.Context) {
	var req ListRequest
	if !bindJSON(c, &req) {
		return
	}

	full, jailRoot, ok := resolveJailed(c, config.G.RootDir, req.BasePath, req.RelPath)
	if !ok {
		return
	}

	items, err := collectItems(full, jailRoot, req.Recursive)
	if err != nil {
		if os.IsNotExist(err) {
			httputil.NotFoundResponse(c, err)
			return
		}
		if os.IsPermission(err) {
			httputil.ForbiddenResponse(c, err)
			return
		}
		httputil.InternalErrorResponse(c, err)
		return
	}

	sort.Slice(items, func(i, j int) bool { return items[i].Path < items[j].Path })

	total := len(items)
	page, pageSize := normalizePaging(req.Page, req.PageSize)
	start := (page - 1) * pageSize
	if start > total {
		start = total
	}
	end := start + pageSize
	if end > total {
		end = total
	}

	httputil.SuccessResponse(c, ListResponse{Total: total, Items: items[start:end]})
}

// collectItems 遍历 dir 下的条目。recursive=true 时用 WalkDir 递归(跳过 dir 自身),
// 否则仅 ReadDir 当前层。Path 为相对 jailRoot 的路径。
func collectItems(dir, jailRoot string, recursive bool) ([]FileItem, error) {
	items := make([]FileItem, 0)

	if recursive {
		err := filepath.WalkDir(dir, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if path == dir {
				return nil
			}
			item, ferr := newFileItem(path, jailRoot, d)
			if ferr != nil {
				return ferr
			}
			items = append(items, item)
			return nil
		})
		return items, err
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	for _, entry := range entries {
		item, ferr := newFileItem(filepath.Join(dir, entry.Name()), jailRoot, entry)
		if ferr != nil {
			return nil, ferr
		}
		items = append(items, item)
	}
	return items, nil
}

// newFileItem 由目录条目构造 FileItem。sha256 恒为 nil, 由 apiserver 回填去重表缓存值。
func newFileItem(absPath, jailRoot string, d fs.DirEntry) (FileItem, error) {
	info, err := d.Info()
	if err != nil {
		return FileItem{}, err
	}
	relPath, err := filepath.Rel(jailRoot, absPath)
	if err != nil {
		return FileItem{}, err
	}

	item := FileItem{
		Path:       relPath,
		Name:       info.Name(),
		IsDir:      info.IsDir(),
		Size:       info.Size(),
		ModifiedAt: formatTime(info.ModTime()),
		Sha256:     nil,
	}
	if !info.IsDir() {
		item.Mime = detectMimeByExt(info.Name())
	}
	return item, nil
}

// normalizePaging 归一化分页参数: page 最小为 1, pageSize 落在 (0, maxPageSize] 内。
func normalizePaging(page, pageSize int) (int, int) {
	if page < 1 {
		page = 1
	}
	if pageSize <= 0 {
		pageSize = defaultPageSize
	}
	if pageSize > maxPageSize {
		pageSize = maxPageSize
	}
	return page, pageSize
}
