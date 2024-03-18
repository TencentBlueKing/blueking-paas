variable "BUILD_IMAGE_NAME" {
  default = ""
}

variable "STACK_BUILDER_TAG" {
  default = "latest"
}

variable "RUN_IMAGE_NAME" {
  default = ""
}

variable "STACK_RUNNER_TAG" {
  default = "latest"
}


function "build_image_name" {
  params = [stack_id, override]
  result = equal(override, "") ? (equal(stack_id, "heroku-18") ? "mirrors.tencent.com/bkpaas/build-heroku-bionic": "mirrors.tencent.com/bkpaas/build-heroku-jammy") : override
}

function "run_image_name" {
  params = [stack_id, override]
  result = equal(override, "") ? (equal(stack_id, "heroku-18") ? "mirrors.tencent.com/bkpaas/run-heroku-bionic": "mirrors.tencent.com/bkpaas/run-heroku-jammy") : override
}


target "heroku-build-bionic" {
  dockerfile = "build.Dockerfile"
  args = {
    TAG = "18.v27"
    STACK_ID = "heroku-18"
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
  tags = ["${build_image_name("heroku-18", BUILD_IMAGE_NAME)}:${STACK_BUILDER_TAG}"]
  platforms = ["linux/amd64"]
}

target "heroku-run-bionic" {
  dockerfile = "run.Dockerfile"
  args = {
    TAG = "18.v27"
    STACK_ID = "heroku-18"
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
  tags = ["${run_image_name("heroku-18", RUN_IMAGE_NAME)}:${STACK_RUNNER_TAG}"]
  platforms = ["linux/amd64"]
}


target "heroku-build-jammy" {
  dockerfile = "build.Dockerfile"
  args = {
    TAG = "22.v122"
    STACK_ID = "heroku-22"
    sources = <<EOF
        deb http://mirrors.tencent.com/ubuntu/ jammy main restricted universe multiverse
        deb http://mirrors.tencent.com/ubuntu/ jammy-security main restricted universe multiverse
        deb http://mirrors.tencent.com/ubuntu/ jammy-updates main restricted universe multiverse
        #deb http://mirrors.tencent.com/ubuntu/ jammy-proposed main restricted universe multiverse
        #deb http://mirrors.tencent.com/ubuntu/ jammy-backports main restricted universe multiverse
        deb-src http://mirrors.tencent.com/ubuntu/ jammy main restricted universe multiverse
        deb-src http://mirrors.tencent.com/ubuntu/ jammy-security main restricted universe multiverse
        deb-src http://mirrors.tencent.com/ubuntu/ jammy-updates main restricted universe multiverse
        #deb-src http://mirrors.tencent.com/ubuntu/ jammy-proposed main restricted universe multiverse
        #deb-src http://mirrors.tencent.com/ubuntu/ jammy-backports main restricted universe multiverse
    EOF

    packages = <<EOF
        libssl-dev
        libc6-dev
        default-libmysqlclient-dev
    EOF
  }
  tags = ["${build_image_name("heroku-22", BUILD_IMAGE_NAME)}:${STACK_BUILDER_TAG}"]
  platforms = ["linux/amd64"]
}

target "heroku-run-jammy" {
  dockerfile = "run.Dockerfile"
  args = {
    TAG = "22.v122"
    STACK_ID = "heroku-22"
    sources = <<EOF
        deb http://mirrors.tencent.com/ubuntu/ jammy main restricted universe multiverse
        deb http://mirrors.tencent.com/ubuntu/ jammy-security main restricted universe multiverse
        deb http://mirrors.tencent.com/ubuntu/ jammy-updates main restricted universe multiverse
        #deb http://mirrors.tencent.com/ubuntu/ jammy-proposed main restricted universe multiverse
        #deb http://mirrors.tencent.com/ubuntu/ jammy-backports main restricted universe multiverse
        deb-src http://mirrors.tencent.com/ubuntu/ jammy main restricted universe multiverse
        deb-src http://mirrors.tencent.com/ubuntu/ jammy-security main restricted universe multiverse
        deb-src http://mirrors.tencent.com/ubuntu/ jammy-updates main restricted universe multiverse
        #deb-src http://mirrors.tencent.com/ubuntu/ jammy-proposed main restricted universe multiverse
        #deb-src http://mirrors.tencent.com/ubuntu/ jammy-backports main restricted universe multiverse
    EOF

    packages = <<EOF
        libssl-dev
        libc6-dev
        default-libmysqlclient-dev
    EOF
  }
  tags = ["${run_image_name("heroku-22", RUN_IMAGE_NAME)}:${STACK_RUNNER_TAG}"]
  platforms = ["linux/amd64"]
}