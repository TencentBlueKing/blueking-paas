<template>
  <div class="input-list-container">
    <bk-form
      :label-width="0"
      :model="formData"
      ref="formRef"
      ext-cls="input-list-form-cls"
    >
      <bk-form-item
        label=""
        v-for="(item, index) in formData.servers"
        :required="true"
        :rules="ruleServers"
        :icon-offset="58"
        :property="'servers.' + index + '.value'"
        :key="index"
      >
        <bk-input v-model="item.value">
          <template slot="append">
            <i
              v-show="serversLength > 1"
              class="paasng-icon paasng-minus-circle-shape"
              @click="delServer(index)"
            ></i>
            <i
              v-show="serversLength - 1 === index"
              class="paasng-icon paasng-plus-circle-shape"
              @click="addServer()"
            ></i>
          </template>
        </bk-input>
      </bk-form-item>
    </bk-form>
  </div>
</template>

<script>
export default {
  name: 'InputList',
  data() {
    return {
      formData: {
        servers: [{ value: '' }],
      },
      ruleServers: [
        {
          required: true,
          message: '请输入',
          trigger: 'blur',
        },
      ],
    };
  },
  computed: {
    serversLength() {
      return this.formData.servers.length;
    },
  },
  methods: {
    addServer() {
      this.formData.servers.push({ value: '' });
    },
    delServer(index) {
      this.formData.servers.splice(index, 1);
    },
    validate() {
      return this.$refs.formRef.validate();
    },
    getData() {
      return this.formData.servers.map((v) => v.value);
    },
  },
};
</script>

<style lang="scss" scoped>
.input-list-container {
  .input-list-form-cls {
    display: flex;
    flex-direction: column;
    /deep/ .bk-form-item {
      margin-top: 8px !important;
      &:first-child {
        margin-top: 0 !important;
      }
    }
    /deep/ .group-append {
      flex-shrink: 0;
      width: 52px;
      border: none !important;
    }
    /deep/ .bk-form-input {
      border-radius: 2px !important;
    }
    .paasng-icon {
      cursor: pointer;
      margin-left: 10px;
      line-height: 32px;
      font-size: 16px;
      color: #979ba5;
    }
  }
}
</style>
