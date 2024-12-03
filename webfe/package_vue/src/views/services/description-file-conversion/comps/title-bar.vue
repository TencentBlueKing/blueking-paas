<template>
  <div class="title-bar card-style">
    <div class="logo">
      <i class="paasng-icon paasng-process-file"></i>
    </div>
    <div class="info">
      <p class="sub-title">{{ $t('app_desc.yaml 是描述蓝鲸应用的配置文件。') }}</p>
      <p>
        {{ $t('specVersion: 3 是针对云原生应用设计的最新规范，可以定义进程服务、可观测性等所有云原生应用的功能。') }}
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TitleBar',
  data() {
    return {};
  },
};
</script>

<style lang="scss" scoped>
.title-bar {
  height: 80px;
  padding: 0 16px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  .logo {
    margin-right: 12px;
    i {
      font-size: 32px;
      color: #a3c5fd;
    }
  }
  .info {
    font-size: 14px;
    color: #313238;
    line-height: 26px;
  }
}
</style>
