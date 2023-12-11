variable "BUILD_IMAGE_NAME" {
  default = "mirrors.tencent.com/bkpaas/build-heroku-bionic"
}

variable "STACK_BUILDER_TAG" {
  default = "latest"
}

variable "RUN_IMAGE_NAME" {
  default = "mirrors.tencent.com/bkpaas/run-heroku-bionic"
}

variable "STACK_RUNNER_TAG" {
  default = "latest"
}


target "heroku-build" {
  dockerfile = "build.Dockerfile"
  args = {
    sources = <<EOF
        deb http://mirrors.cloud.tencent.com/ubuntu/ bionic main restricted universe multiverse
        deb http://mirrors.cloud.tencent.com/ubuntu/ bionic-security main restricted universe multiverse
        deb http://mirrors.cloud.tencent.com/ubuntu/ bionic-updates main restricted universe multiverse
        deb http://mirrors.cloud.tencent.com/ubuntu/ bionic-proposed main restricted universe multiverse
        deb http://mirrors.cloud.tencent.com/ubuntu/ bionic-backports main restricted universe multiverse
        #deb-src http://mirrors.cloud.tencent.com/ubuntu/ bionic main restricted universe multiverse
        #deb-src http://mirrors.cloud.tencent.com/ubuntu/ bionic-security main restricted universe multiverse
        #deb-src http://mirrors.cloud.tencent.com/ubuntu/ bionic-updates main restricted universe multiverse
        #deb-src http://mirrors.cloud.tencent.com/ubuntu/ bionic-proposed main restricted universe multiverse
        #deb-src http://mirrors.cloud.tencent.com/ubuntu/ bionic-backports main restricted universe multiverse
    EOF

    packages = <<EOF
        libssl-dev
        libc6-dev
        default-libmysqlclient-dev
    EOF
  }
  tags = ["${BUILD_IMAGE_NAME}:${STACK_BUILDER_TAG}"]
  platforms = ["linux/amd64"]
}

target "heroku-run" {
  dockerfile = "run.Dockerfile"
  args = {
    sources = <<EOF
        deb http://mirrors.cloud.tencent.com/ubuntu/ bionic main restricted universe multiverse
        deb http://mirrors.cloud.tencent.com/ubuntu/ bionic-security main restricted universe multiverse
        deb http://mirrors.cloud.tencent.com/ubuntu/ bionic-updates main restricted universe multiverse
        deb http://mirrors.cloud.tencent.com/ubuntu/ bionic-proposed main restricted universe multiverse
        deb http://mirrors.cloud.tencent.com/ubuntu/ bionic-backports main restricted universe multiverse
        #deb-src http://mirrors.cloud.tencent.com/ubuntu/ bionic main restricted universe multiverse
        #deb-src http://mirrors.cloud.tencent.com/ubuntu/ bionic-security main restricted universe multiverse
        #deb-src http://mirrors.cloud.tencent.com/ubuntu/ bionic-updates main restricted universe multiverse
        #deb-src http://mirrors.cloud.tencent.com/ubuntu/ bionic-proposed main restricted universe multiverse
        #deb-src http://mirrors.cloud.tencent.com/ubuntu/ bionic-backports main restricted universe multiverse
    EOF

    packages = <<EOF
        libssl-dev
        libc6-dev
        default-libmysqlclient-dev
    EOF
  }
  tags = ["${RUN_IMAGE_NAME}:${STACK_RUNNER_TAG}"]
  platforms = ["linux/amd64"]
}