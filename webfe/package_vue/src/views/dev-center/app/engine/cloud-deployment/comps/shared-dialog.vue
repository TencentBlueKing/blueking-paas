<template>
  <bk-dialog
    v-model="isShowDialog"
    width="480"
    :title="$t('从其它模块共享服务实例')"
    :mask-close="false"
    ext-cls="paasng-service-export-dialog-cls"
    header-position="left"
    @after-leave="handleAfterLeave"
  >
    <label class="title">{{ curTitle }}</label>
    <bk-select
      v-model="curModuleValue"
      style="width: 430px;"
      :loading="selectLoading"
      :popover-min-width="430"
      :multiple="false"
      searchable
    >
      <bk-option
        v-for="option in list"
        :id="option.id"
        :key="option.id"
        :name="option.name"
      />
    </bk-select>
    <section class="tips">
      {{ $t('该功能用于模块间共享服务实例信息，比如共享数据库配置等。确认共享后，当前模块将获得目标模块对应服务实例的的所有环境变量。') }}
    </section>
    <template slot="footer">
      <div>
        <bk-button
          theme="primary"
          :disabled="disbaled"
          :loading="loading"
          @click="handleSumbit"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button @click="handleCancel">
          {{ $t('取消') }}
        </bk-button>
      </div>
    </template>
  </bk-dialog>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin';
export default {
  name: '',
  mixins: [appBaseMixin],
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    name: {
      type: String,
      default: '',
    },
    data: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      isShowDialog: false,
      curModuleValue: '',
      selectLoading: false,
      list: [],
      loading: false,
    };
  },
  computed: {
    disbaled() {
      return this.curModuleValue === '';
    },
    curTitle() {
      return this.data.display_name ? `${this.$t('已启用 ')}${this.data.display_name}${this.$t('服务的模块：')}` : '';
    },
  },
  watch: {
    show: {
      handler(value) {
        this.isShowDialog = !!value;
        if (this.isShowDialog) {
          this.fetchData();
        }
      },
      immediate: true,
    },
  },
  methods: {
    async fetchData() {
      this.selectLoading = true;
      try {
        const res = await this.$store.dispatch('service/getServicesShareableModule', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          serviceId: this.data.uuid,
        });
        this.list = res;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.selectLoading = false;
      }
    },

    async handleSumbit() {
      this.loading = true;
      try {
        await this.$store.dispatch('service/createSharedAttachment', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          serviceId: this.data.uuid,
          ref_module_name: this.list.find(item => item.id === this.curModuleValue).name,
        });
        this.$emit('on-success');
        this.handleCancel();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.loading = false;
      }
    },

    handleCancel() {
      this.$emit('on-cancel');
      this.$emit('update:show', false);
    },

    handleAfterLeave() {
      this.curModuleValue = '';
      this.$emit('update:show', false);
      this.$emit('on-after-leave');
    },
  },
};
</script>
  <style lang="scss">
      .paasng-service-export-dialog-cls {
          .title {
              line-height: 24px;
          }
          .tips {
              margin-top: 10px;
              padding: 8px;
              background: #f5f6fa;
              border-radius: 2px;
              font-size: 12px;
              word-break: break-all;
          }
      }
  </style>

