<template>
  <div class="default-component-details">
    <!-- 默认组件详情样式 -->
    <DetailsRow
      :label-width="80"
      :label="`${$t('组件介绍')}：`"
      :value="introduceMap[data?.name] || '--'"
    />
    <DetailsRow
      :label-width="80"
      :is-full="true"
      :align="'flex-start'"
    >
      <template slot="label">{{ `${$t('组件配置')}：` }}</template>
      <div slot="value">
        <div
          class="config"
          v-if="isBkIngressNginx"
        >
          <DetailsRow
            :label-width="80"
            :label="`${$t('访问方式')}：`"
            :value="accessMethod"
          />
          <template v-if="accessMethod === 'nodePort'">
            <DetailsRow
              :label-width="80"
              :label="`HTTP ${$t('端口')}：`"
              :value="values?.service?.nodePorts?.http"
            />
            <DetailsRow
              :label-width="80"
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
      <template slot="label">{{ `${$t('组件状态')}：` }}</template>
      <div
        slot="value"
        class="status-wrapper"
      >
        <i
          class="paasng-icon paasng-check-circle-shape"
          v-if="data?.status === 'installed'"
        ></i>
        <i
          class="paasng-icon paasng-unfinished"
          v-else
        ></i>
        <span>{{ localLanguage === 'en' ? data?.status : COMPONENT_STATUS[data?.status] || '--' }}</span>
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
  },
  data() {
    return {
      COMPONENT_STATUS,
      isEditorSideslider: false,
      isShowDetail: false,
      // 与其他组件展示不同
      specialComponent: 'bk-ingress-nginx',
      introduceMap: {
        'bk-ingress-nginx': this.$t('为应用提供负载均等功能。'),
        'bkpaas-app-operator': this.$t('云原生应用的控制引擎，必须安装后才能部署应用。'),
        'bcs-general-pod-autoscaler': this.$t('Saas 服务水平扩缩容组件，支持基于资源使用情况调整服务副本数量。'),
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
      return this.values?.hostNetwork ? 'hostNerwork' : 'nodePort';
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
