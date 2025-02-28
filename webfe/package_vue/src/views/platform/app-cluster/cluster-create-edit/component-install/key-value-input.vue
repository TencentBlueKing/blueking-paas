<template>
  <div class="input-list-container">
    <bk-form
      :label-width="0"
      :model="formData"
      ref="formRef"
      ext-cls="input-list-form-cls"
    >
      <div class="item-title">
        <div>{{ $t('键') }}</div>
        <div>{{ $t('值') }}</div>
      </div>
      <div
        v-for="(item, index) in formData.nodes"
        class="form-item-wrapper"
        :key="index"
      >
        <bk-form-item
          label=""
          :required="true"
          :rules="ruleServers"
          :property="'nodes.' + index + '.key'"
          :key="index + 'key'"
        >
          <bk-input v-model="item.key"></bk-input>
        </bk-form-item>
        <span class="sign">=</span>
        <bk-form-item
          label=""
          :required="true"
          :rules="ruleServers"
          :property="'nodes.' + index + '.value'"
          :key="index + 'value'"
        >
          <bk-input v-model="item.value"></bk-input>
        </bk-form-item>
        <div class="tools">
          <i
            v-show="nodesLength > 1"
            class="paasng-icon paasng-minus-circle-shape"
            @click="delServer(index)"
          ></i>
          <i
            v-show="nodesLength - 1 === index"
            class="paasng-icon paasng-plus-circle-shape"
            @click="addServer()"
          ></i>
        </div>
      </div>
    </bk-form>
  </div>
</template>

<script>
export default {
  name: 'InputList',
  data() {
    return {
      formData: {
        nodes: [{ key: '', value: '' }],
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
    nodesLength() {
      return this.formData.nodes.length;
    },
  },
  methods: {
    addServer() {
      this.formData.nodes.push({ key: '', value: '' });
    },
    delServer(index) {
      this.formData.nodes.splice(index, 1);
    },
    validate() {
      return this.$refs.formRef.validate();
    },
    getData() {
      const data = {};
      this.formData.nodes.forEach((v) => {
        data[v.key] = v.value;
      });
      return data;
    },
  },
};
</script>

<style lang="scss" scoped>
.input-list-container {
  .item-title {
    display: flex;
    align-items: center;
    color: #4d4f56;
    div {
      flex: 1;
      &:last-child {
        margin-left: -28px;
      }
    }
  }
  .form-item-wrapper {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    .sign {
      font-size: 14px;
      color: #4d4f56;
      margin: 0 8px;
    }
    .tools {
      min-width: 52px;
      flex-shrink: 0;
    }
  }
  .input-list-form-cls {
    display: flex;
    flex-direction: column;
    /deep/ .bk-form-item {
      width: 100%;
      margin-top: 0 !important;
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
