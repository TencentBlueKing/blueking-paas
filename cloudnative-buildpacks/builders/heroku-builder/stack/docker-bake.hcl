variable "STACK_BUILDER_TAG" {
  default = "latest"
}

variable "STACK_RUNNER_TAG" {
  default = "latest"
}

variable "APT_SOURCES" {
  default = <<EOF
  deb http://mirrors.cloud.tencent.com/ubuntu/ noble main restricted universe multiverse
  deb http://mirrors.cloud.tencent.com/ubuntu/ noble-security main restricted universe multiverse
  deb http://mirrors.cloud.tencent.com/ubuntu/ noble-updates main restricted universe multiverse
  EOF
}

variable "BASE_PACKAGES" {
  default = <<EOF
  libssl-dev libc6-dev default-libmysqlclient-dev
  EOF
}


target "heroku-build-noble" {
  dockerfile = "build.Dockerfile"
  args = {
    TAG = "24.v149"
    STACK_ID = "heroku-24"
    sources = "${APT_SOURCES}"
    packages = "${BASE_PACKAGES}"
  }
  tags = ["mirrors.tencent.com/bkpaas/build-heroku-noble:${STACK_BUILDER_TAG}"]
  platforms = ["linux/amd64"]
}

target "heroku-run-noble" {
  dockerfile = "run.Dockerfile"
  args = {
    TAG = "24.v149"
    STACK_ID = "heroku-24"
    sources = "${APT_SOURCES}"
    packages = "${BASE_PACKAGES}"
  }
  tags = ["mirrors.tencent.com/bkpaas/run-heroku-noble:${STACK_RUNNER_TAG}"]
  platforms = ["linux/amd64"]
}
