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
	defaultPageSize = 100
	maxPageSize     = 500
)

// ListFiles godoc
//
//	@Summary		List files in a volume path
//	@Description	List files under base_path/rel_path with pagination, optionally recursive
//	@Tags			pv
//	@Accept			json
//	@Produce		json
//	@Param			request	query		ListRequest	true	"List request"
//	@Success		200		{object}	ListResponse
//	@Router			/files/list [get]
//
//	@id				ListFiles
func ListFiles(c *gin.Context) {
	var req ListRequest
	if !bindQuery(c, &req) {
		return
	}
	c.Header("Cache-Control", "no-store")

	full, jailRoot, ok := resolveJailed(c, config.G.RootDir, req.BasePath, req.RelPath)
	if !ok {
		return
	}

	items, err := collectItems(full, jailRoot, req.Recursive)
	if err != nil {
		respondErr(c, err)
		return
	}

	sort.Slice(items, func(i, j int) bool { return items[i].Path < items[j].Path })
	page, pageSize := normalizePaging(req.Page, req.PageSize)
	start := min((page-1)*pageSize, len(items))
	end := min(start+pageSize, len(items))

	httputil.SuccessResponse(c, ListResponse{Total: len(items), Items: items[start:end]})
}

// collectItems 遍历 dir: recursive 用 WalkDir(跳过 dir 自身), 否则仅当前层。Path 相对 jailRoot。
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

// newFileItem 由目录条目构造 FileItem, mime 仅按扩展名(不读内容)。sha256 恒为 nil。
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
	}
	if !info.IsDir() {
		item.Mime = detectMimeByExt(info.Name())
	}
	return item, nil
}

// normalizePaging 归一化: page>=1, pageSize 落在 (0, maxPageSize]。
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
