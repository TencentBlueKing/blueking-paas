<template>
  <div class="itsm">
    <status-bar :type="curStatusBarData.type">
      <template #left>
        <!-- 等待审批 -->
        <span class="warning-check-wrapper" v-if="curStatusBarData.type === 'warning'">
          <i class="paasng-icon paasng-paas-remind-fill" />
        </span>
        <!-- 审批通过 -->
        <span class="success-check-wrapper" v-else-if="curStatusBarData.type === 'success'">
          <i class="paasng-icon paasng-correct" />
        </span>
        <!-- 审批不通过 -->
        <span class="error-left-warp flex-row align-items-center" v-else-if="curStatusBarData.type === 'failed'">
          <i class="error-icon paasng-icon paasng-close-circle-shape" />
        </span>
        <!-- 撤销提单 -->
        <span class="interrupted-check-wrapper" v-else>
          <i class="paasng-icon paasng-back2" />
        </span>
        <span class="info-time pl10">
          <span class="info-pending-text"> {{ $t(curStatusBarData.title) }} </span>
        </span>
      </template>
      <template #right>
        <bk-button
          size="small"
          theme="primary"
          :outline="true"
          ext-cls="detail-btn"
          @click="handlerApprovalDetails"
        >
          {{ $t('查看审批详情') }}
        </bk-button>
        <bk-button
          v-if="isCancelBtn"
          size="small"
          theme="primary"
          :outline="true"
          class="ml8"
          ext-cls="detail-btn"
          @click="handlerApprovalDetails"
        >
          {{ $t('撤销提单') }}
        </bk-button>
      </template>
    </status-bar>

    <itsm-info-item :title="$t('提单信息')" :data="ladingData"></itsm-info-item>
    <itsm-info-item :title="$t('申请内容')" :data="applyData"></itsm-info-item>
  </div>
</template>
<script>
import stageBaseMixin from './stage-base-mixin';
import statusBar from './comps/status-bar';
import itsmInfoItem from './comps/itsm-info-item';
import { PLUGIN_ITSM_APPLY, PLUGIN_ITSM_LADING, APPROVALSTATUS, STATUSBARDATA } from '@/common/constants';

// 提单信息
const ladingMap = PLUGIN_ITSM_LADING;

// 申请内容
const applyMap = PLUGIN_ITSM_APPLY;

export default {
  components: {
    statusBar,
    itsmInfoItem,
  },
  mixins: [stageBaseMixin],
  props: {
    pluginData: {
      type: Object,
      default: () => {},
    },
    stageData: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      ladingData: [],
      applyData: [],
    };
  },
  computed: {
    // 手动切换步骤预览，使用详情数据，步骤预览不会改变当前发布的步骤顺序
    itsmData() {
      return this.pluginData.current_stage.itsm_detail?.fields || this.stageData.detail?.fields || [];
    },
    itsmDetail() {
      return this.pluginData.current_stage?.itsm_detail || this.stageData.detail || {};
    },
    curStatusBarData() {
      // approval successful failed interrupted
      const status = this.stageData.status || this.pluginData.current_stage.status;
      const curStatus = APPROVALSTATUS[status];
      return STATUSBARDATA[curStatus];
    },
    isCancelBtn() {
      return this.stageData.detail?.can_withdraw;
    },
  },
  watch: {
    itsmData() {
      this.init();
    },
  },
  mounted() {
    this.init();
  },
  methods: {
    init() {
      if (this.ladingData.length && this.applyData.length) {
        return;
      }
      this.itsmData.forEach((item) => {
        if (ladingMap[item.key]) {
          const data = { ...item, name: ladingMap[item.key] };
          this.ladingData.unshift(data);
        }
        if (applyMap[item.key]) {
          const data = { ...item, name: applyMap[item.key] };
          this.applyData.push(data);
        }
      });
      this.ladingData.unshift({
        name: '单号',
        value: this.itsmDetail.sn,
      });
    },
    // 查看详情
    handlerApprovalDetails() {
      let url = this.pluginData.current_stage?.itsm_detail?.ticket_url;
      if (!url) {
        url = this.stageData?.detail?.ticket_url;
      }
      window.open(url, '_blank');
    },
  },
};
</script>

<style lang="scss" scoped>
  .itsm {
    .wrapper {
      .bk-button.bk-primary.is-outline.detail-btn {
        background: transparent;

        &:hover {
          background: #3a84ff;
          border-color: #3a84ff;
          color: #fff;
        }
      }

      .ml8 {
        margin-left: 8px;
      }

      .error-left-warp {
        i {
          font-size: 24px;
        }
      }
    }
  }
</style>
