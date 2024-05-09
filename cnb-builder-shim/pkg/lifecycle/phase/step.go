package phase

import (
	"os"
	"os/exec"

	"github.com/pkg/errors"
)

// Step describe CNB Build Step
type Step struct {
	Name         string
	EnterMessage string
	Cmd          *exec.Cmd
	options      []CmdOptsProvider
	isExecuted   bool
}

// Execute CNB Build Step
func (s *Step) Execute() error {
	if s.isExecuted {
		return errors.New("Step can not execute twice.")
	}
	s.isExecuted = true
	// Redirect input and output
	if s.Cmd.Stdin == nil {
		s.Cmd.Stdin = os.Stdin
	}
	if s.Cmd.Stdout == nil {
		s.Cmd.Stdout = os.Stdout
	}
	if s.Cmd.Stderr == nil {
		s.Cmd.Stderr = os.Stderr
	}
	for _, provider := range s.options {
		provider(s.Cmd)
	}
	return s.Cmd.Run()
}

// WithCmdOptions add cmd decorators
func (s *Step) WithCmdOptions(opts ...CmdOptsProvider) *Step {
	s.options = append(s.options, opts...)
	return s
}

func makeStep(name string, enterMessage string, cmd *exec.Cmd, opts ...CmdOptsProvider) Step {
	return Step{
		Name:         name,
		EnterMessage: enterMessage,
		Cmd:          cmd,
		options:      opts,
	}
}
