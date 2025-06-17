<template>
  <div class="examples-directory-container">
    <div class="flex-row justify-content-between title-wrapper">
      <div class="f12">
        {{ $t('代码仓库推荐文件结构') }}
        <span class="tips f12 ml10">{{ $t('为确保应用能够正常构建，代码仓库文件请参考以下结构') }}</span>
      </div>
      <a
        :href="GLOBAL.DOC.FILE_LOCATION_DESCRIPTION"
        target="_blank"
        class="f12"
      >
        {{ $t('app_desc.yaml 文件位置说明') }}
        <i class="paasng-icon paasng-jump-link"></i>
      </a>
    </div>
    <TreeTextDisplay
      v-bind="$attrs"
      :rootPath="rootPath"
      :appendPath="appendPath"
      :is-dockerfile="isDockerfile"
      :tip-config="tipConfig"
    />
  </div>
</template>

<script>
import TreeTextDisplay from '@/components/tree-text-display';

export default {
  name: 'ExamplesDirectory',
  components: {
    TreeTextDisplay,
  },
  props: {
    rootPath: {
      type: String,
      default: '',
    },
    appendPath: {
      type: String,
      default: '',
    },
    isDockerfile: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    dockerfileTips() {
      return !this.rootPath
        ? this.$t('在根目录下执行如下命令构建镜像：')
        : this.$t('在 <i>{p}</i> 目录下执行如下命令构建镜像：', { p: this.rootPath });
    },
    tipConfig() {
      return {
        theme: 'light',
        extCls: 'dockerfile-tips-cls',
        html: `<p class="paas-example-tips">${this.dockerfileTips}</p>
        <p class="paas-example-tips">docker build. -f ${
          this.appendPath ? this.appendPath : 'Dockerfile'
        } imagename</p>`,
      };
    },
  },
};
</script>

<style lang="scss" scoped>
.examples-directory-container {
  margin-top: 16px;
  padding: 16px;
  color: #4d4f56;
  background: #f0f1f5;
  border-radius: 2px;
  .title-wrapper {
    line-height: 1;
    margin-bottom: 8px;
  }
  .tips {
    color: #979ba5;
  }
}
</style>
<style lang="scss">
.paas-example-tips {
  font-size: 12px;
  line-height: 20px;
  font-family: monospace;
  i {
    font-style: normal;
    color: #ea3636;
  }
}
</style>
