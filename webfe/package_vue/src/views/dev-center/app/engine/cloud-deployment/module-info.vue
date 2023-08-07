<template>
  <div class="module-info-container">
    <div class="base-info-container flex-row align-items-center">
      <span class="base-info-title">
        {{ $t('基本信息-title') }}
      </span>
      <div class="edit-container" @click="handleProcessNameEdit(panel.name, index)">
        <i class="paasng-icon paasng-edit-2 pl10" />
        {{ $t('编辑') }}
      </div>
    </div>
    <div class="form-detail mt20 pb20 border-b">
      <bk-form
        :model="buildData">
        <bk-form-item
          :label="$t('托管方式：')">
          <span class="form-text">{{ buildData.type || '--' }}</span>
        </bk-form-item>
        <bk-form-item
          :label="$t('镜像仓库：')">
          <span class="form-text">{{ buildData.image || '--' }}</span>
        </bk-form-item>
        <bk-form-item
          :label="$t('镜像凭证：')">
          <span class="form-text">{{ buildData.imagePullPolicy || '--' }}</span>
        </bk-form-item>
      </bk-form>
    </div>
  </div>
</template>
<script>import appBaseMixin from '@/mixins/app-base-mixin';
import _ from 'lodash';
export default {
  mixins: [appBaseMixin],
  props: {
    cloudAppData: {
      type: Object,
      default: {},
    },
  },
  data() {
    return {
      isLoading: false,
      buildData: {},
      localCloudAppData: {},
    };
  },
  computed: {
    curAppModule() {
      console.log('this.$store.state.curAppModule', this.$store.state.curAppModule);
      return this.$store.state.curAppModule;
    },
  },
  watch: {
    cloudAppData: {
      handler(val) {
        if (val.spec) {
          this.localCloudAppData = _.cloneDeep(val);
          this.buildData = this.localCloudAppData.spec.build || {};
        }
      },
      immediate: true,
      deep: true,
    },
  },
};
</script>
<style lang="scss" scoped>
  .module-info-container{
    padding: 0 20px 20px;
    .base-info-title{
      color: #313238;
      font-size: 14px;
      font-weight: bold;
    }
    .edit-container{
      color: #3A84FF;
      font-size: 12px;
    }

    .form-detail{
      .form-text{
          color: #313238;
        }
    }

    .border-b{
      border-bottom: 1px solid #dcdee5;
    }
  }
</style>
