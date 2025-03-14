<template>
  <div class="default-component-details">
    <!-- 默认组件详情样式 -->
    <DetailsRow
      :label-width="80"
      :label="removePrefix('组件介绍')"
      :value="$t(introduceMap[data?.name]) || '--'"
    />
    <DetailsRow
      :label-width="80"
      :is-full="true"
      :align="'flex-start'"
    >
      <template slot="label">{{ removePrefix('组件配置') }}</template>
      <div slot="value">
        <div
          class="config"
          v-if="isBkIngressNginx"
        >
          <DetailsRow
            :label-width="80"
            :label="`${$t('访问方式')}：`"
            :value="accessMethod ?? '--'"
          />
          <template v-if="accessMethod !== null">
            <template v-if="accessMethod === 'nodePort'">
              <DetailsRow
                :label-width="80"
                :label="`HTTP ${$t('端口')}：`"
                :value="values?.service?.nodePorts?.http || '--'"
              />
              <DetailsRow
                :label-width="80"
                :label="`HTTPS ${$t('端口')}：`"
                :value="values?.service?.nodePorts?.https || '--'"
              />
            </template>
            <template v-else>
              <!-- hostNetwork -->
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
          </template>
        </div>
        <template v-else>
          {{ $t('使用默认 values 部署即可。') }}
          <bk-button
            class="values-btn"
            :text="true"
            size="small"
            @click="handleViewValues"
          >
            <i class="paasng-icon paasng-file-5"></i>
            <span>{{ $t('查看 Values') }}</span>
          </bk-button>
        </template>
      </div>
    </DetailsRow>
    <DetailsRow
      :label-width="80"
      :is-full="true"
      :align="'flex-start'"
    >
      <template slot="label">{{ removePrefix('组件状态') }}</template>
      <div
        slot="value"
        class="status-wrapper"
      >
        <IconStatus
          v-if="data?.status !== 'installing'"
          :icon-class="statusMap[data?.status]?.iconClass"
          :icon-color="statusMap[data?.status]?.color"
          :label="localLanguage === 'en' ? data?.status : COMPONENT_STATUS[data?.status] || '--'"
        />
        <template v-else>
          <round-loading
            size="mini"
            class="mr5"
          />
          <span>{{ localLanguage === 'en' ? data?.status : COMPONENT_STATUS[data?.status] || '--' }}</span>
        </template>
        <bk-button
          v-if="data?.status === 'installed'"
          :text="true"
          size="small"
          @click="handleViewDetail"
        >
          <i class="paasng-icon paasng-file-5"></i>
          <span>{{ $t('查看详情') }}</span>
        </bk-button>
      </div>
    </DetailsRow>
    <!-- 查看 values 侧栏 -->
    <EditorSideslider
      :show.sync="isEditorSideslider"
      :title="$t('查看 Values')"
      :value="valuesData"
      :read-only="true"
    />
    <!-- 查看组件详情侧栏 -->
    <DetailComponentsSideslider
      :show.sync="isShowDetail"
      :name="data?.name"
      :detail-data="detailData"
    />
  </div>
</template>

<script>
import DetailsRow from '@/components/details-row';
import IconStatus from '@/components/icon-status';
import EditorSideslider from '@/components/editor-sideslider';
import DetailComponentsSideslider from './detail-components-sideslider.vue';
import { COMPONENT_STATUS } from '@/common/constants';
export default {
  name: 'DefaultComponentDetails',
  props: {
    data: {
      type: Object,
      default: () => {},
    },
    detailData: {
      type: Object,
      default: () => {},
    },
  },
  components: {
    DetailsRow,
    EditorSideslider,
    DetailComponentsSideslider,
    IconStatus,
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
      isEditorSideslider: false,
      isShowDetail: false,
      // 与其他组件展示不同
      specialComponent: 'bk-ingress-nginx',
      introduceMap: {
        'bk-ingress-nginx':
          'Nginx Ingress 控制器，基于 Nginx 实现 HTTP/HTTPS 流量路由、负载均衡、自定义域名、URL 路径规则等功能。',
        'bkapp-log-collection':
          '将应用的各类日志采集到 ElasticSearch 集群，以支持后续查询标准输出、预定义的结构化、Nginx 接入层等日志。',
        'bkpaas-app-operator':
          '云原生应用的关键基建，是开发者中心基于 k8s 能力实现的 operator，承担着云原生应用相关资源的管理，调度等职责。',
        'bcs-general-pod-autoscaler':
          '蓝鲸容器管理平台（BCS）提供的增强型 Pod 水平扩缩容组件，支持按各类指标对应用集成副本数量进行扩缩容。',
      },
    };
  },
  computed: {
    isBkIngressNginx() {
      return this.specialComponent === this.data.name;
    },
    values() {
      return this.detailData?.values || {};
    },
    accessMethod() {
      if (typeof this.values?.hostNetwork === 'boolean') {
        return this.values.hostNetwork ? 'hostNetwork' : 'nodePort';
      }
      return null;
    },
    valuesData() {
      return JSON.stringify(this.values, null, 2);
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  methods: {
    // 查看组件详情
    handleViewDetail() {
      this.isShowDetail = true;
    },
    // 查看values
    handleViewValues() {
      this.isEditorSideslider = true;
    },
    // 英文环境下去掉组件前缀
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
.default-component-details {
  .values-btn {
    padding: 0;
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
  }
  i.paasng-file-5 {
    font-size: 14px;
    margin-right: 3px;
  }
  .config {
    padding: 6px 12px;
    background: #ffffff;
    border-radius: 2px;
    .tag {
      margin-right: 4px;
    }
  }
}
</style>
