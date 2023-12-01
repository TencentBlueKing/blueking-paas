variable "IMAGE_NAME" {
  default = "mirrors.tencent.com/bkpaas/heroku-stack-bionic"
}

variable "BUILDER_TAG" {
  default = "build"
}

variable "RUNNER_TAG" {
  default = "run"
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
  tags = ["${IMAGE_NAME}:${BUILDER_TAG}"]
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
  tags = ["${IMAGE_NAME}:${RUNNER_TAG}"]
}