<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    show-mask
    width="680"
    @shown="init"
  >
    <div slot="header">
      <div class="header-box">
        <span>{{ $t('编辑组件配置') }}</span>
        <div>
          <bk-button
            class="values-btn"
            :text="true"
            @click="$emit('show-values', name)"
          >
            <i class="paasng-icon paasng-file-5 mr5"></i>
            <span>{{ $t('查看 Values') }}</span>
          </bk-button>
        </div>
      </div>
    </div>
    <div
      class="sideslider-content"
      slot="content"
    >
      <div class="access-method">
        <div
          v-for="(item, index) in accessMethod"
          :key="index"
          class="item"
          :class="{ active: item.value === formData.hostNetwork }"
          @click="handleSwitch(item)"
        >
          <div class="left-icon">
            <i :class="['paasng-icon', item.icon]"></i>
          </div>
          <div class="info">
            <p class="title">{{ item.title }}</p>
            <p class="tip">{{ item.tip }}</p>
          </div>
        </div>
      </div>
      <bk-form
        :label-width="155"
        :model="formData"
        form-type="vertical"
        ref="formRef"
        ext-cls="component-form-cls"
      >
        <bk-form-item
          v-for="item in pageFormOptions"
          :label="$t(item.label)"
          :required="item.required"
          :property="item.property"
          :rules="item.rules"
          :key="item.label"
          :error-display-type="'normal'"
        >
          <ConfigInput
            v-if="item.type === 'input'"
            v-model="formData[item.property]"
            :type="item.type"
          />
          <KeyValueInput
            v-else
            :is-title="true"
            :is-sign="true"
            ref="keyValueInput"
          />
        </bk-form-item>
        <bk-form-item class="mt20">
          <bk-button
            style="margin-right: 8px"
            theme="primary"
            :loading="saveLoading"
            ext-cls="btn-cls"
            @click.stop.prevent="submitData"
          >
            {{ $t('保存') }}
          </bk-button>
          <bk-button
            ext-cls="btn-cls"
            theme="default"
            @click="closeSideslider"
          >
            {{ $t('取消') }}
          </bk-button>
        </bk-form-item>
      </bk-form>
    </div>
  </bk-sideslider>
</template>

<script>
import ConfigInput from '../comps/config-input.vue';
import KeyValueInput from '../comps/key-value-input.vue';
import i18n from '@/language/i18n.js';
import { cloneDeep } from 'lodash';

// 必填规则
const requiredRule = [
  {
    required: true,
    message: i18n.t('必填项'),
    trigger: 'blur',
  },
];
export default {
  name: 'ComponentConfigEdit',
  components: {
    ConfigInput,
    KeyValueInput,
  },
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
      default: () => {},
    },
    clusterId: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      formData: {
        http: '',
        https: '',
        hostNetwork: false,
      },
      // 使用组件详情进行更新
      nodePortOptions: [
        {
          label: 'HTTP 端口',
          type: 'input',
          property: 'http',
          required: true,
          rules: [...requiredRule],
        },
        {
          label: 'HTTPS 端口',
          type: 'input',
          property: 'https',
          required: true,
          rules: [...requiredRule],
        },
      ],
      hostNetworkOptions: [
        {
          label: '节点标签',
          type: 'arr-input',
          property: 'resources',
          required: true,
        },
      ],
      accessMethod: [
        {
          title: 'nodePort',
          tip: this.$t(
            '使用 CLB 作为接入层，监听器根据域名转发至不同集群的 NodePort。Nginx 同样根据域名配置 upstream，指向相应的集群 NodePort。'
          ),
          icon: 'paasng-branch-line',
          value: false,
        },
        {
          title: 'hostNetwork',
          tip: this.$t('主机网络模式下，bk-ingress-nginx 会直接监听在对应节点的 80 和 443 端口。'),
          icon: 'paasng-host',
          value: true,
        },
      ],
      // 保存按钮loading
      saveLoading: false,
    };
  },
  computed: {
    sidesliderVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
    values() {
      return this.data?.values ?? {};
    },
    isHostNetwork() {
      return this.formData.hostNetwork;
    },
    pageFormOptions() {
      if (this.isHostNetwork) {
        return this.hostNetworkOptions;
      }
      return this.nodePortOptions;
    },
  },
  methods: {
    init() {
      const { hostNetwork = false, service } = this.values;
      this.formData = {
        http: service?.nodePorts?.http || '',
        https: service?.nodePorts?.https || '',
        hostNetwork,
      };
    },
    reset() {
      this.formData = {
        http: '',
        https: '',
        hostNetwork: false,
      };
    },
    closeSideslider() {
      this.sidesliderVisible = false;
      this.reset();
    },
    handleSwitch(item) {
      this.formData.hostNetwork = item.value;
      if (this.isHostNetwork) {
        this.$nextTick(() => {
          const { nodeSelector = {} } = this.values;
          // 节点标签
          const nodes = Object.entries(nodeSelector).map(([key, value]) => {
            return {
              key: key,
              value: value,
            };
          });
          this.$refs.keyValueInput[0]?.setData(nodes);
        });
      }
    },
    submitData() {
      let validateArr = [this.$refs.formRef.validate()];
      if (this.isHostNetwork) {
        validateArr.push(this.$refs.keyValueInput[0]?.validate());
      }
      Promise.all(validateArr)
        .then((r) => {
          const { hostNetwork } = this.formData;
          let data = cloneDeep(this.values);
          data.hostNetwork = hostNetwork;
          if (this.isHostNetwork) {
            data.nodeSelector = this.$refs.keyValueInput[0]?.getData();
          } else {
            const { http, https } = this.formData;
            data.service.nodePorts = { http, https };
          }
          this.updateComponent(data);
        })
        .catch((e) => {
          console.warn(e);
        });
    },
    // 更新组件配置
    async updateComponent(data) {
      this.saveLoading = true;
      try {
        await this.$store.dispatch('tenant/updateComponent', {
          clusterName: this.clusterId,
          componentName: this.name,
          data,
        });
        // 成功提示
        this.$paasMessage({
          theme: 'success',
          message: this.$t('编辑成功！'),
        });
        this.closeSideslider();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.saveLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
@import '~@/assets/css/mixins/border-active-logo.scss';
.header-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sideslider-content {
  padding: 24px 40px;
  .component-form-cls {
    /deep/ .bk-label {
      color: #4d4f56;
    }
  }
  .btn-cls {
    min-width: 88px;
  }
  .access-method {
    margin-bottom: 24px;
    .item {
      position: relative;
      display: flex;
      align-items: center;
      border: 1px solid #c4c6cc;
      border-radius: 2px;
      height: 68px;
      border-radius: 2px;
      cursor: pointer;
      &:first-child {
        margin-bottom: 8px;
        i {
          transform: rotate(90deg);
        }
      }
      &.active {
        border-color: #3a84ff;
        .left-icon {
          border-color: #3a84ff;
          color: #3a84ff;
        }
        @include border-active-logo;
      }
      .left-icon {
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 68px;
        height: 100%;
        border-right: 1px solid #c4c6cc;
        background: #f5f7fa;
        color: #979ba5;
        i {
          font-size: 24px;
        }
      }
      .info {
        padding: 10px 12px;
      }
      .title {
        font-weight: 700;
        font-size: 14px;
        color: #313238;
        line-height: 22px;
      }
      .tip {
        font-size: 12px;
        color: #4d4f56;
        line-height: 20px;
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
  }
}
</style>
