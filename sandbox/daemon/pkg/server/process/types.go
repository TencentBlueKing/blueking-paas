package process

// ExecuteRequest is the request to execute a command.
type ExecuteRequest struct {
	Command string  `json:"command" validate:"required"`
	Timeout *uint32 `json:"timeout,omitempty" validate:"optional"`
	// Current working directory
	Cwd *string `json:"cwd,omitempty" validate:"optional"`
}

// ExecuteResponse is the response to an ExecuteRequest.
type ExecuteResponse struct {
	ExitCode int    `json:"exitCode"`
	Output   string `json:"output"`
}
