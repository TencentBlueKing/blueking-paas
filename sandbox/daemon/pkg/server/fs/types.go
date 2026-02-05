package fs

type CreateFolderRequest struct {
	Path string `json:"path" validate:"required"`
	Mode string `json:"mode,omitempty" validate:"optional"`
}
