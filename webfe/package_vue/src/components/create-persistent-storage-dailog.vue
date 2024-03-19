<template>
  <bk-dialog
    v-model="storageDialogConfig.visible"
    theme="primary"
    :width="640"
    :mask-close="false"
    :title="$t('新增持久存储')"
    :auto-close="false"
    header-position="left"
    @after-leave="handlerCancel"
  >
    <div slot="footer">
      <bk-button
        theme="primary"
        :loading="storageDialogConfig.isLoading"
        @click="handlerConfirm"
      >
        {{ $t('确定') }}
      </bk-button>
      <bk-button
        theme="default"
        @click.stop="handlerCancel"
      >
        {{ $t('取消') }}
      </bk-button>
    </div>
    <section class="storage-dialog-content">
      <bk-alert type="info">
        <div slot="title">
          {{ $t('持久存储会申请对应容量的腾讯云 CFS，新建后就会产生实际的费用，请按需申请。') }}
          <bk-button
            theme="primary"
            text
            style="font-size: 12px"
            @click="viewBillingMethod"
          >
            {{ $t('查看计费方式') }}
          </bk-button>
        </div>
      </bk-alert>
      <bk-form
        :label-width="localLanguage === 'en' ? 160 : 85"
        :model="createPersistentStorageData"
        ext-cls="form-cls"
        style="margin-top: 16px"
      >
        <bk-form-item
          :label="$t('生效环境')"
          :required="true"
          :property="'stage'"
        >
          <bk-radio-group
            v-model="createPersistentStorageData.stage"
            @change="handlerChange"
          >
            <bk-radio :value="'stag'">{{ $t('预发布环境') }}</bk-radio>
            <bk-radio :value="'prod'">{{ $t('生产环境') }}</bk-radio>
          </bk-radio-group>
        </bk-form-item>
        <bk-form-item
          :label="$t('容量')"
          :required="true"
          :property="'capacity'"
        >
          <bk-radio-group v-model="createPersistentStorageData.capacity">
            <bk-radio :value="'1Gi'">1Gi</bk-radio>
            <bk-radio :value="'2Gi'" :disabled="preReleaseEnvironment">2Gi</bk-radio>
            <bk-radio :value="'4Gi'" :disabled="preReleaseEnvironment">4Gi</bk-radio>
          </bk-radio-group>
          <p class="capacity-tips">{{ $t('容量无法更改，请合理评估容量') }}</p>
        </bk-form-item>
      </bk-form>
    </section>
  </bk-dialog>
</template>

<script>
const defaultSourceType = 'PersistentStorage';
export default {
  name: 'CreatePersistentStorageDailog',
  model: {
    prop: 'value',
    event: 'change',
  },
  props: {
    value: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      storageDialogConfig: {
        visible: false,
        isLoading: false,
      },
      createPersistentStorageData: {
        stage: 'stag',
        capacity: '1Gi',
      },
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    preReleaseEnvironment() {
      return this.createPersistentStorageData.stage === 'stag';
    },
  },
  watch: {
    value(newVal) {
      this.storageDialogConfig.visible = newVal;
    },
  },
  methods: {
    // 新建存储
    async handlerConfirm() {
      this.storageDialogConfig.isLoading = true;
      const data = {
        environment_name: this.createPersistentStorageData.stage,
        source_type: defaultSourceType,
        persistent_storage_source: {
          storage_size: this.createPersistentStorageData.capacity,
        },
      };
      try {
        await this.$store.dispatch('persistentStorage/createPersistentStorage', {
          appCode: this.appCode,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('新建成功！'),
        });
        this.handlerCancel();
        // 重新获取列表
        this.$emit('get-list');
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.storageDialogConfig.isLoading = false;
      }
    },
    // 新建存储数据重置
    handlerCancel() {
      this.$emit('change', false);
      setTimeout(() => {
        this.createPersistentStorageData = {
          stage: 'stag',
          capacity: '1Gi',
        };
      }, 500);
    },
    // 查看计费方式
    viewBillingMethod() {
      const url = 'https://cloud.tencent.com/document/product/582/47378';
      window.open(url, '_blank');
    },
    handlerChange() {
      this.createPersistentStorageData.capacity = '1Gi';
    },
  },
};
</script>

<style lang="scss" scoped>
.storage-dialog-content {
  :deep(.icon-info) {
    line-height: 22px;
  }
}
.capacity-tips {
  color: #979BA5;
  font-size: 12px;
}
</style>
