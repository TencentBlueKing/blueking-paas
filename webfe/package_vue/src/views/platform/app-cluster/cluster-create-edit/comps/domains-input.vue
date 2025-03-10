<template>
  <div class="domains-input-container">
    <bk-form
      :label-width="0"
      :model="formData"
      ref="formRef"
      ext-cls="domains-input-form-cls"
    >
      <bk-form-item
        label=""
        v-for="(item, index) in formData.list"
        :required="true"
        :rules="rule"
        :icon-offset="iconOffset"
        :property="'list.' + index + '.name'"
        :key="index"
      >
        <bk-input v-model="item.name">
          <template slot="append">
            <span
              v-bk-tooltips="{
                content: $t('若启用 HTTPS，请在“共享证书”中托管证书，或者在外部网关中配置证书。'),
                width: 200,
              }"
            >
              <bk-checkbox v-model="item.https_enabled">
                {{ `${$t('启用')} HTTPS` }}
              </bk-checkbox>
            </span>
            <i
              v-show="!(dataLength === 1 && index === 0)"
              class="paasng-icon paasng-delete"
              @click="delRow(index)"
            ></i>
            <bk-button
              v-show="dataLength - 1 === index"
              :text="true"
              title="primary"
              ext-cls="add-icon"
              @click="addRow"
            >
              <i class="paasng-icon paasng-plus-thick"></i>
              <span>{{ $t('新增域名') }}</span>
            </bk-button>
          </template>
        </bk-input>
      </bk-form-item>
    </bk-form>
  </div>
</template>

<script>
export default {
  name: 'DomainsInput',
  props: {
    data: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      formData: {
        list: [{ name: '', https_enabled: false, reserved: false }],
      },
      rule: [
        {
          required: true,
          message: '请输入',
          trigger: 'blur',
        },
      ],
    };
  },
  computed: {
    dataLength() {
      return this.formData.list.length;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    iconOffset() {
      if (this.localLanguage === 'en') {
        return this.dataLength === 1 ? 131 : 159;
      }
      return this.dataLength === 1 ? 115 : 143;
    },
  },
  methods: {
    setFormData(data) {
      if (data.length) {
        this.formData.list = [...data];
      }
    },
    addRow() {
      this.formData.list.push({ name: '', https_enabled: false, reserved: false });
    },
    delRow(index) {
      this.formData.list.splice(index, 1);
    },
    validate() {
      return this.$refs.formRef.validate();
    },
    getData() {
      return this.formData.list;
    },
  },
};
</script>

<style lang="scss" scoped>
.domains-input-container {
  .domains-input-form-cls {
    display: flex;
    flex-direction: column;
    /deep/ .bk-form-item {
      margin-top: 8px !important;
      &:first-child {
        margin-top: 0 !important;
      }
    }
    /deep/ .group-append {
      display: flex;
      align-items: center;
      position: relative;
      margin-left: 8px;
      flex-shrink: 0;
      border: none !important;
    }
    /deep/ .bk-form-input {
      border-radius: 2px !important;
    }
    .paasng-icon {
      cursor: pointer;
      line-height: 32px;
      font-size: 16px;
      transform: translateY(0px);
      &.paasng-delete {
        margin-left: 12px;
        color: #ea3636;
      }
      &.paasng-plus-thick {
        margin-right: 3px;
      }
    }
    .add-icon {
      position: absolute;
      display: flex;
      align-items: center;
      right: 0;
      top: 50%;
      transform: translate(calc(100% + 15px), -50%);
    }
    /deep/ .bk-checkbox-text {
      border-bottom: 1px dashed #979ba5;
    }
  }
}
</style>
