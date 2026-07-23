package volumefs

import (
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/gabriel-vasile/mimetype"
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

	root, dir, ok := openJailedRoot(c, config.G.RootDir, req.BasePath, req.RelPath)
	if !ok {
		return
	}
	defer root.Close() // nolint

	// 列目录语义要求目标本身是目录; 指向文件(或指向文件的中段路径)属客户端误用, 返回 400 而非 500。
	// Root.Stat 跟随但限制 symlink, 不存在仍走 404。
	info, err := root.Stat(dir)
	if err != nil {
		respondErr(c, err)
		return
	}
	if !info.IsDir() {
		httputil.BadRequestResponse(c, fmt.Errorf("not a directory: %q", req.RelPath))
		return
	}

	modifiedTimeRange, err := parseModifiedTimeRange(req.Since, req.Until)
	if err != nil {
		httputil.BadRequestResponse(c, err)
		return
	}
	page, pageSize := normalizePaging(req.Page, req.PageSize)
	collected, err := collectItems(root, dir, req.Recursive, modifiedTimeRange)
	if err != nil {
		respondErr(c, err)
		return
	}

	sort.Slice(collected, func(i, j int) bool { return collected[i].path < collected[j].path })
	count := len(collected)
	extraData := ListExtraData{}
	for _, entry := range collected {
		if entry.info.IsDir() {
			extraData.Directories++
		} else {
			extraData.Files++
		}
	}
	items := make([]FileItem, 0, pageSize)
	start := pageStart(page, pageSize)
	if start < count {
		end := start + min(pageSize, count-start)
		for _, entry := range collected[start:end] {
			item, err := newFileItem(root, entry.path, entry.info)
			if err != nil {
				respondErr(c, err)
				return
			}
			items = append(items, item)
		}
	}

	httputil.SuccessResponse(c, ListResponse{Count: count, Results: items, ExtraData: extraData})
}

type collectedItem struct {
	path string
	info os.FileInfo
}

// collectItems traverses a directory using root-relative names. Every stat and
// open stays below the os.Root, including entries swapped to symlinks mid-walk.
// timeRange 按 since <= 修改时间 <= until 筛选条目；任一边界可省略。
// 它先收集全部匹配条目的轻量元数据，供调用方全局排序后分页。
func collectItems(root *os.Root, dir string, recursive bool, timeRange modifiedTimeRange) ([]collectedItem, error) {
	items := make([]collectedItem, 0)

	appendItem := func(path string) error {
		info, err := root.Stat(path)
		if err != nil {
			return err
		}
		if timeRange.enabled() {
			if !timeRange.includes(info.ModTime()) {
				return nil
			}
		}
		items = append(items, collectedItem{path: path, info: info})
		return nil
	}

	var walk func(string) error
	walk = func(current string) error {
		directory, err := root.Open(current)
		if err != nil {
			return err
		}
		entries, err := directory.ReadDir(-1)
		closeErr := directory.Close()
		if err != nil {
			return err
		}
		if closeErr != nil {
			return closeErr
		}
		for _, entry := range entries {
			path := filepath.Join(current, entry.Name())
			if err := appendItem(path); err != nil {
				return err
			}
			// Match filepath.WalkDir: directory symlinks are listed but not followed.
			if recursive && entry.IsDir() {
				if err := walk(path); err != nil {
					return err
				}
			}
		}
		return nil
	}

	if err := walk(dir); err != nil {
		return nil, err
	}
	return items, nil
}

type modifiedTimeRange struct {
	since *time.Time
	until *time.Time
}

func (r modifiedTimeRange) enabled() bool {
	return r.since != nil || r.until != nil
}

func (r modifiedTimeRange) includes(modifiedAt time.Time) bool {
	return (r.since == nil || !modifiedAt.Before(*r.since)) &&
		(r.until == nil || !modifiedAt.After(*r.until))
}

// parseModifiedTimeRange 解析 since 和 until 查询参数。空值表示对应边界不限制，非空值必须为 RFC3339 时间。
func parseModifiedTimeRange(since, until string) (modifiedTimeRange, error) {
	parsedSince, err := parseFilterTime("since", since)
	if err != nil {
		return modifiedTimeRange{}, err
	}
	parsedUntil, err := parseFilterTime("until", until)
	if err != nil {
		return modifiedTimeRange{}, err
	}
	if parsedSince != nil && parsedUntil != nil && parsedSince.After(*parsedUntil) {
		return modifiedTimeRange{}, fmt.Errorf("since must be less than or equal to until")
	}
	return modifiedTimeRange{since: parsedSince, until: parsedUntil}, nil
}

func parseFilterTime(name, value string) (*time.Time, error) {
	if value == "" {
		return nil, nil
	}
	parsed, err := time.Parse(time.RFC3339, value)
	if err != nil {
		return nil, fmt.Errorf("invalid %s %q: must be RFC3339", name, value)
	}
	return &parsed, nil
}

func pageStart(page, pageSize int) int {
	if page-1 > math.MaxInt/pageSize {
		return math.MaxInt
	}
	return (page - 1) * pageSize
}

// newFileItem builds metadata from a root-relative path. sha256 is always nil.
func newFileItem(root *os.Root, path string, info os.FileInfo) (FileItem, error) {
	item := FileItem{
		Path:       path,
		Name:       info.Name(),
		IsDir:      info.IsDir(),
		Size:       info.Size(),
		ModifiedAt: formatTime(info.ModTime()),
	}
	if !info.IsDir() {
		m, err := detectMime(root, path)
		if err != nil {
			return FileItem{}, err
		}
		item.Mime = m.String()
	}
	return item, nil
}

func detectMime(root *os.Root, name string) (*mimetype.MIME, error) {
	f, err := root.Open(name)
	if err != nil {
		return nil, err
	}
	defer f.Close() // nolint
	return mimetype.DetectReader(f)
}

// normalizePaging 归一化: page>=1, pageSize 落在 (0, maxPageSize]
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
