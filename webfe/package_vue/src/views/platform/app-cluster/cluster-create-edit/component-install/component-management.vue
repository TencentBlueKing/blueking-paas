<template>
  <div :class="['component-management', { required: component.required }]">
    <div class="component-header mb15">
      <div
        class="icon-warpper"
        :style="{ backgroundColor: statusColors[component?.status] }"
      >
        <i class="paasng-icon paasng-plugin"></i>
      </div>
      <h3>{{ component.name }}</h3>
    </div>
    <div
      class="component-content"
      v-bkloading="{ isLoading: loading, zIndex: 10 }"
    >
      <DetailsRow
        :label-width="80"
        :label="`${$t('组件介绍')}：`"
        :value="getComponentIntroduction(component.name)"
      />
      <DetailsRow
        v-if="isBkIngressNginx"
        :label-width="80"
        :is-full="true"
        :align="'flex-start'"
      >
        <template slot="label">{{ `${$t('组件配置')}：` }}</template>
        <div slot="value">
          <div class="tools-btns">
            <bk-button
              :text="true"
              title="primary"
              @click="handleComponentEdit"
            >
              <i class="paasng-icon paasng-edit-2"></i>
              {{ $t('编辑') }}
            </bk-button>
            <bk-button
              class="values-btn"
              :text="true"
              @click="handleViewValues"
            >
              <i class="paasng-icon paasng-file-5 mr5"></i>
              <span>{{ $t('查看 Values') }}</span>
            </bk-button>
          </div>
          <div class="config">
            <DetailsRow
              :label-width="90"
              :label="`${$t('访问方式')}：`"
              :value="accessMethod"
            >
              <template slot="value">
                <span>{{ accessMethod }}</span>
                <span class="tip">
                  <i class="paasng-icon paasng-info-line ml8"></i>
                  <span v-if="accessMethod === 'nodePort'">
                    {{
                      $t(
                        '使用 CLB 作为接入层，监听器根据域名转发至不同集群的 NodePort。Nginx 同样根据域名配置 upstream，指向相应的集群 NodePort。'
                      )
                    }}
                  </span>
                  <span v-else>
                    {{ $t('主机网络模式下，bk-ingress-nginx 会直接监听在对应节点的 80 和 443 端口。') }}
                  </span>
                </span>
              </template>
            </DetailsRow>
            <!-- nodePort -->
            <template v-if="accessMethod === 'nodePort'">
              <DetailsRow
                :label-width="90"
                :label="`HTTP ${$t('端口')}：`"
                :value="values?.service?.nodePorts?.http || '--'"
              />
              <DetailsRow
                :label-width="90"
                :label="`HTTPS ${$t('端口')}：`"
                :value="values?.service?.nodePorts?.https"
              />
            </template>
            <template v-else>
              <!-- hostNerwork -->
              <DetailsRow
                :label-width="80"
                :label="`${$t('节点标签')}：`"
                :align="'flex-start'"
              >
                <div slot="value">
                  <span v-if="!values.nodeSelector?.length">--</span>
                  <span
                    v-else
                    v-for="(val, key) in values.nodeSelector"
                    class="tag"
                    :key="key"
                  >
                    {{ key }} = {{ val }}
                  </span>
                </div>
              </DetailsRow>
            </template>
          </div>
        </div>
      </DetailsRow>
      <DetailsRow
        :label-width="80"
        :label="`${$t('组件说明')}：`"
      >
        <div slot="value">
          {{ getComponentDescription(component.name) }}
          <bk-button
            v-if="!isBkIngressNginx"
            class="values-btn"
            :text="true"
            @click="handleViewValues"
          >
            <i class="paasng-icon paasng-file-5 mr5"></i>
            <span>{{ $t('查看 Values') }}</span>
          </bk-button>
        </div>
      </DetailsRow>
      <DetailsRow
        :label-width="80"
        :is-full="true"
        :align="'flex-start'"
      >
        <template slot="label">{{ `${$t('组件状态')}：` }}</template>
        <div
          slot="value"
          class="status-wrapper"
        >
          <IconStatus
            v-if="component?.status !== 'installing'"
            :icon-class="statusMap[component?.status].iconClass"
            :icon-color="statusMap[component?.status].color"
            :label="localLanguage === 'en' ? component?.status : COMPONENT_STATUS[component?.status] || '--'"
          />
          <template v-else>
            <round-loading
              size="mini"
              class="mr5"
            />
            <span>{{ localLanguage === 'en' ? component?.status : COMPONENT_STATUS[component?.status] || '--' }}</span>
          </template>
          <bk-button
            v-if="component?.status === 'installed'"
            :text="true"
            size="small"
            @click="handleViewDetail"
          >
            <i class="paasng-icon paasng-file-5"></i>
            <span>{{ $t('查看详情') }}</span>
          </bk-button>
        </div>
      </DetailsRow>
      <!-- 安装操作 -->
      <div class="install-btns">
        <!-- 未安装/安装失败 -->
        <span
          v-if="['not_installed', 'installation_failed'].includes(component?.status)"
          v-bk-tooltips="disabledTooltipsConfig"
          class="btn-wrapper"
        >
          <bk-button
            :theme="'primary'"
            :disabled="!isInstalled"
          >
            {{ component?.status === 'not_installed' ? $t('安装') : $t('重新安装') }}
          </bk-button>
        </span>
        <!-- 已安装可更新 -->
        <span
          v-else-if="component?.status === 'installed'"
          v-bk-tooltips="disabledTooltipsConfig"
          class="btn-wrapper"
        >
          <bk-button
            :theme="'primary'"
            :outline="true"
            :disabled="!isInstalled"
          >
            {{ $t('更新') }}
          </bk-button>
        </span>
      </div>
    </div>
  </div>
</template>

<script>
import DetailsRow from '@/components/details-row';
import IconStatus from '@/components/icon-status';
import { COMPONENT_STATUS } from '@/common/constants';

export default {
  components: {
    DetailsRow,
    IconStatus,
  },
  props: {
    component: {
      type: Object,
      default: () => {},
    },
    details: {
      type: Object,
      default: () => {},
    },
    loading: {
      type: Boolean,
      default: false,
    },
    clusterSource: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      COMPONENT_STATUS,
      statusMap: {
        not_installed: {
          color: '#f59500',
          iconClass: 'paasng-unfinished',
        },
        installed: {
          color: '#18c0a1',
          iconClass: 'paasng-check-circle-shape',
        },
        installation_failed: {
          color: '#ea3636',
          iconClass: 'paasng-close-circle-shape',
        },
      },
      statusColors: {
        not_installed: '#F8B64F',
        installing: '#3A84FF',
        installed: '#18C0A1',
        installation_failed: '#E71818',
      },
      disabledTooltipsConfig: {
        content: this.$t('非 BCS 集群需要手动安装集群组件'),
        disabled: this.isInstalled,
      },
    };
  },
  computed: {
    isBkIngressNginx() {
      return this.component.name === 'bk-ingress-nginx';
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    accessMethod() {
      return this.details?.hostNetwork ? 'hostNerwork' : 'nodePort';
    },
    values() {
      return this.details?.values || {};
    },
    // 只有bcs允许安装更新
    isInstalled() {
      return this.clusterSource === 'bcs';
    },
  },
  methods: {
    // 获取组件介绍
    getComponentIntroduction(name) {
      const introduction = {
        'bk-ingress-nginx': '为应用提供负载均等功能。',
        'bkapp-log-collection':
          '将所有应用日志统一采集到 ElasticSearch，包含应用标准输出日志、开发框架定义的结构化日志、应用接入层日志等。',
        'bkpaas-app-operator': '云原生应用的控制引擎，必须安装后才能部署应用。',
        'bcs-general-pod-autoscaler': 'BCS 提供的增强型扩缩容组件。',
      };
      return introduction[name] || '--';
    },
    getComponentDescription(name) {
      const description = {
        'bkapp-log-collection': '已经根据上一步填写的日志路径和 ElasticSearch 集群信息生成 values。',
      };
      return description[name] || this.$t('使用默认 values 部署即可。');
    },
    // 查看组件详情
    handleViewDetail() {
      this.$emit('show-detail', this.component.name);
    },
    // 查看values
    handleViewValues() {
      this.$emit('show-values', this.component.name);
    },
    // 组件编辑
    handleComponentEdit() {
      this.$emit('show-edit', this.component.name);
    },
  },
};
</script>

<style lang="scss" scoped>
.component-management {
  padding-left: 52px;
  &.required h3::after {
    content: '*';
    height: 8px;
    line-height: 1;
    color: #ea3636;
    font-size: 12px;
    position: absolute;
    top: 50%;
    transform: translate(3px, -50%);
  }
}
.component-header {
  position: relative;
  .icon-warpper {
    display: flex;
    align-items: center;
    justify-content: center;
    position: absolute;
    left: 0;
    top: 50%;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    font-size: 20px;
    transform: translate(-52px, -50%);
    i {
      color: #fff;
    }
  }
  h3 {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
  }
}
.component-content {
  position: relative;
  padding: 16px;
  margin-bottom: 24px;
  background: #f5f7fa;
  border-radius: 8px;
  &::before {
    content: '';
    position: absolute;
    top: 2px;
    left: -32px;
    width: 2px;
    height: calc(100% + 4px);
    background: #dcdee5;
    border-radius: 1px;
  }
  .tools-btns {
    display: flex;
    align-items: center;
    gap: 25px;
    margin: 5px 0 6px 0;
    /deep/ .bk-primary {
      line-height: 22px;
    }
  }
  /deep/ .details-row {
    .label,
    .value {
      font-size: 14px;
    }
  }
  .status-wrapper {
    i {
      font-size: 14px;
      margin-right: 5px;
    }
    .paasng-check-circle-shape {
      color: #18c0a1;
    }
    .paasng-unfinished {
      color: #f59500;
    }
    .paasng-close-circle-shape {
      color: #ea3636;
    }
  }
  .tip {
    font-size: 12px;
    color: #979ba5;
  }
  .config {
    padding: 12px 24px;
    background: #ffffff;
    border-radius: 2px;
    .tag {
      margin-right: 4px;
    }
    /deep/ .details-row {
      .label,
      .value {
        font-size: 12px;
      }
    }
    .ml8 {
      margin-left: 8px;
    }
  }
  .install-btns {
    margin-left: 80px;
    .btn-wrapper {
      display: inline-block;
    }
  }
}
</style>
