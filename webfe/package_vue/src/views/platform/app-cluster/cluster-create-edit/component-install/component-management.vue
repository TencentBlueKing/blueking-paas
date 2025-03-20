<template>
  <div :class="['component-management', { required: component.required }]">
    <div class="component-header mb15">
      <div
        class="icon-warpper"
        :style="{ backgroundColor: statusColors[detailStatus] }"
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
        :label-width="labelWidth"
        :label="removePrefix('组件介绍')"
        :value="getComponentIntroduction(component.name)"
      />
      <DetailsRow
        v-if="isBkIngressNginx"
        :label-width="labelWidth"
        :is-full="true"
        :align="'flex-start'"
      >
        <template slot="label">{{ removePrefix('组件配置') }}</template>
        <div slot="value">
          <div class="tools-btns">
            <!-- bk-ingress-nginx 允许编辑 -->
            <bk-button
              :text="true"
              title="primary"
              :disabled="!isInstalled"
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
              :label-width="labelWidth"
              :label="`${$t('访问方式')}：`"
              :value="accessMethod"
            >
              <template slot="value">
                <span>{{ accessMethod ?? '--' }}</span>
                <span
                  class="tip"
                  v-if="accessMethod !== null"
                >
                  <i class="paasng-icon paasng-info-line ml8"></i>
                  <span v-if="accessMethod === 'nodePort'">
                    {{ $t('使用 CLB 作为接入层，监听器将流量转发到集群节点的指定的 NodePort。') }}
                  </span>
                  <span v-else>
                    {{ $t('直接使用节点主机网络，nginx 将会将流量转发到节点的 80 & 443 端口。') }}
                  </span>
                </span>
              </template>
            </DetailsRow>
            <template v-if="accessMethod !== null">
              <!-- nodePort -->
              <template v-if="accessMethod === 'nodePort'">
                <DetailsRow
                  :label-width="labelWidth"
                  :label="`HTTP ${$t('端口')}：`"
                  :value="values?.service?.nodePorts?.http || '--'"
                />
                <DetailsRow
                  :label-width="labelWidth"
                  :label="`HTTPS ${$t('端口')}：`"
                  :value="values?.service?.nodePorts?.https || '--'"
                />
              </template>
              <template v-else>
                <!-- hostNetwork -->
                <DetailsRow
                  :label-width="labelWidth"
                  :label="`${$t('节点标签')}：`"
                  :align="'flex-start'"
                >
                  <div slot="value">
                    <span v-if="!Object.keys(values.nodeSelector)?.length">--</span>
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
            </template>
          </div>
        </div>
      </DetailsRow>
      <DetailsRow
        v-if="!isBkIngressNginx"
        :label-width="labelWidth"
        :label="removePrefix('组件说明')"
      >
        <div slot="value">
          {{ getComponentDescription(component.name) }}
          <bk-button
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
        :label-width="labelWidth"
        :is-full="true"
        :align="'flex-start'"
      >
        <template slot="label">{{ removePrefix('组件状态') }}</template>
        <div
          slot="value"
          class="status-wrapper"
        >
          <!-- 组件状态：使用详情中的 status 实时更新状态 -->
          <IconStatus
            v-if="detailStatus !== 'installing'"
            :icon-class="statusMap[detailStatus]?.iconClass"
            :icon-color="statusMap[detailStatus]?.color"
            :label="localLanguage === 'en' ? detailStatus : COMPONENT_STATUS[detailStatus] || $t('未安装')"
            :font-size="14"
          />
          <template v-else>
            <round-loading
              size="mini"
              class="mr5"
              style="margin-left: 0"
            />
            <span class="status-text">
              {{ localLanguage === 'en' ? detailStatus : COMPONENT_STATUS[detailStatus] || $t('未安装') }}
            </span>
          </template>
          <bk-button
            v-if="['installed', 'installation_failed'].includes(detailStatus)"
            :text="true"
            class="view-detail"
            @click="handleViewDetail"
          >
            <i class="paasng-icon paasng-file-5"></i>
            <span>{{ $t('查看详情') }}</span>
          </bk-button>
        </div>
      </DetailsRow>
      <!-- 安装操作 -->
      <div
        class="install-btns"
        :style="{ marginLeft: labelWidth + 'px' }"
      >
        <!-- 未安装/安装失败/更新中按钮也需要显示-loading状态 -->
        <span
          v-if="['not_installed', 'installation_failed', 'installing'].includes(detailStatus)"
          v-bk-tooltips="disabledTooltipsConfig"
          class="btn-wrapper"
        >
          <bk-button
            :theme="'primary'"
            :disabled="!isInstalled"
            :loading="componentBtnLoading || btnLoading || detailStatus === 'installing'"
            @click="getDiffVersion(detailStatus)"
          >
            {{ detailStatus === 'not_installed' ? $t('安装') : $t('重新安装') }}
          </bk-button>
        </span>
        <!-- 已安装可更新/安装中按钮也需要显示-loading状态 -->
        <span
          v-else-if="['installed', 'installing'].includes(detailStatus)"
          v-bk-tooltips="disabledTooltipsConfig"
          class="btn-wrapper"
        >
          <bk-button
            :theme="'primary'"
            :outline="true"
            :disabled="!isInstalled"
            :loading="componentBtnLoading || btnLoading || detailStatus === 'installing'"
            @click="getDiffVersion(detailStatus)"
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
    btnLoading: {
      type: Boolean,
      default: false,
    },
    clusterSource: {
      type: String,
      default: '',
    },
    clusterId: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      COMPONENT_STATUS,
      statusMap: {
        not_installed: {
          color: '#c4c6cc',
          iconClass: 'paasng-time-filled',
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
      componentBtnLoading: false,
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
      if (typeof this.values?.hostNetwork === 'boolean') {
        return this.values.hostNetwork ? 'hostNetwork' : 'nodePort';
      }
      return null;
    },
    values() {
      return this.details?.values || {};
    },
    // 只有bcs允许安装更新
    isInstalled() {
      return this.clusterSource === 'bcs';
    },
    labelWidth() {
      return this.localLanguage === 'en' ? 100 : 80;
    },
    disabledTooltipsConfig() {
      return {
        content: this.$t('非 BCS 集群需要手动安装集群组件'),
        disabled: this.isInstalled,
      };
    },
    detailStatus() {
      return this.details?.status || 'not_installed';
    },
  },
  methods: {
    // 获取组件介绍
    getComponentIntroduction(name) {
      const introduction = {
        'bk-ingress-nginx':
          'Nginx Ingress 控制器，基于 Nginx 实现 HTTP/HTTPS 流量路由、负载均衡、自定义域名、URL 路径规则等功能。',
        'bkapp-log-collection':
          '将应用的各类日志采集到 ElasticSearch 集群，以支持后续查询标准输出、预定义的结构化、Nginx 接入层等日志。',
        'bkpaas-app-operator':
          '云原生应用的关键基建，是开发者中心基于 k8s 能力实现的 operator，承担着云原生应用相关资源的管理，调度等职责。',
        'bcs-general-pod-autoscaler':
          '蓝鲸容器管理平台（BCS）提供的增强型 Pod 水平扩缩容组件，支持按各类指标对应用集成副本数量进行扩缩容。',
      };
      return this.$t(introduction[name]) || '--';
    },
    getComponentDescription(name) {
      const description = {
        'bkapp-log-collection': this.$t('已经根据前面步骤填写的配置生成 Values。'),
      };
      return description[name] || this.$t('使用默认 Values 即可，无需额外配置。');
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
    // 安装/更新/重新安装
    async getDiffVersion(status) {
      const h = this.$createElement;
      this.componentBtnLoading = true;
      try {
        const ret = await this.$store.dispatch('tenant/getDiffVersion', {
          clusterName: this.clusterId, // 暂时为固定值
          componentName: this.component.name,
        });
        // current_version 当前版本（安装原始版本应该是 --）、latest_version 最新版本
        this.$bkInfo({
          title: this.$t('组件版本更新确认'),
          extCls: 'diff-version-info-cls',
          subHeader: h('div', [
            h('div', { class: ['tips'] }, `${this.$t('当前版本')}：${ret.current_version || '--'}`),
            h('div', { class: ['tips'] }, `${this.$t('最新版本')}：${ret.latest_version || '--'}`),
          ]),
          confirmFn: () => {
            const params = this.isBkIngressNginx ? this.values : {};
            this.updateComponent({ values: params }, status);
          },
          cancelFn: () => {
            this.componentBtnLoading = false;
          },
        });
      } catch (e) {
        this.componentBtnLoading = false;
        this.catchErrorHandler(e);
      }
    },
    // 更新组件配置
    async updateComponent(data = {}, status) {
      try {
        await this.$store.dispatch('tenant/updateComponent', {
          clusterName: this.clusterId,
          componentName: this.component.name,
          data,
        });
        const msg = status === 'installed' ? this.$t('更新成功') : this.$t('已下发安装任务');
        this.$paasMessage({
          theme: 'success',
          message: msg,
        });
        // 轮询获取组件详情
        this.$emit('polling', this.component.name);
        // 手动改变状态为 installing
        this.$emit('change-status', this.component.name, 'installing');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.componentBtnLoading = false;
      }
    },
    // 获取中英文label值
    removePrefix(str, prefix = '组件') {
      if (this.localLanguage === 'en') {
        return `${this.$t(str.slice(prefix.length))}：`;
      }
      return `${this.$t(str)}：`;
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
    display: flex;
    align-items: center;
    i {
      font-size: 14px;
      margin-right: 5px;
    }
    .paasng-check-circle-shape {
      color: #18c0a1;
    }
    .paasng-time-filled {
      color: #c4c6cc;
    }
    .paasng-close-circle-shape {
      color: #ea3636;
    }
    .status-text {
      font-size: 14px;
      color: #313238;
    }
    .view-detail {
      margin-left: 18px;
      height: auto;
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
    margin-top: 8px;
    .btn-wrapper {
      display: inline-block;
    }
  }
}
</style>
<style lang="scss">
.diff-version-info-cls .bk-info-box .bk-dialog-sub-header {
  .tips {
    color: #63656e;
    line-height: 32px;
  }
}
</style>
