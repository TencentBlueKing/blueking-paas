<template>
  <section :class="['paasng-kv-list', { en: isEnglish }]">
    <div class="item">
      <div class="key">{{ $t('申请人') }}：</div>
      <div class="value">
        {{ curRecord.applied_by }}
      </div>
    </div>
    <div
      v-if="!isComponentApi"
      class="item"
    >
      <div class="key">
        {{ `${$t('授权维度')}：` }}
      </div>
      <div class="value">
        {{ curRecord.grant_dimension === 'resource' ? $t('按资源') : $t('按网关') }}
      </div>
    </div>
    <div class="item">
      <div class="key">
        {{ $t('有效时间：') }}
      </div>
      <div class="value">
        {{ curRecord.expire_days === 0 ? $t('永久') : Math.ceil(curRecord.expire_days / 30) + $t('个月') }}
      </div>
    </div>
    <div class="item">
      <div class="key">
        {{ $t('申请理由：') }}
      </div>
      <div class="value">
        {{ curRecord.reason || '--' }}
      </div>
    </div>
    <div class="item">
      <div class="key">
        {{ $t('申请时间：') }}
      </div>
      <div class="value">
        {{ curRecord.applied_time }}
      </div>
    </div>
    <div class="item">
      <div class="key">
        {{ $t('审批人：') }}
      </div>
      <div class="value">
        {{ getHandleBy(curRecord.handled_by) || '--' }}
      </div>
    </div>
    <div class="item">
      <div class="key">
        {{ $t('审批时间：') }}
      </div>
      <div class="value">
        {{ curRecord.handled_time || '--' }}
      </div>
    </div>
    <div class="item">
      <div class="key">
        {{ $t('审批状态：') }}
      </div>
      <div class="value">
        {{ $t(curRecord.apply_status_display) || '--' }}
      </div>
    </div>
    <div class="item">
      <div class="key">
        {{ `${$t('审批内容')}：` }}
      </div>
      <div
        class="value"
        style="line-height: 22px; padding-top: 10px"
      >
        {{ curRecord.comment || '--' }}
      </div>
    </div>
    <div class="item">
      <div class="key">
        {{ isComponentApi ? $t('系统名称：') : $t('网关名称：') }}
      </div>
      <div class="value">
        {{ (isComponentApi ? curRecord.system_name : curRecord.api_name) || '--' }}
      </div>
    </div>
    <div
      v-if="isComponentApi"
      class="item"
    >
      <div class="key">
        {{ `API ${$t('列表')}：` }}
      </div>
      <div
        class="value"
        style="line-height: 22px; padding-top: 10px"
      >
        <bk-table
          :size="'small'"
          :data="curRecord.components"
          :header-cell-style="{ background: '#fafbfd', borderRight: 'none' }"
          ext-cls="paasng-expand-table"
        >
          <div slot="empty">
            <table-empty empty />
          </div>
          <bk-table-column
            prop="name"
            :label="$t('API名称')"
          />
          <bk-table-column
            prop="method"
            :label="$t('审批状态')"
          >
            <template slot-scope="prop">
              <template v-if="prop.row['apply_status'] === 'rejected'">
                <span class="paasng-icon paasng-reject" />
                {{ $t('驳回') }}
              </template>
              <template v-else-if="prop.row['apply_status'] === 'pending'">
                <round-loading ext-cls="applying" />
                {{ $t('待审批') }}
              </template>
              <template v-else>
                <span class="paasng-icon paasng-pass" />
                {{ prop.row['apply_status'] === 'approved' ? $t('通过') : $t('部分通过') }}
              </template>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </div>
    <div
      v-else
      class="item"
    >
      <div class="key">
        {{ `API ${$t('列表')}：` }}
      </div>
      <div
        v-if="curRecord.grant_dimension === 'resource'"
        class="value"
        style="line-height: 22px; padding-top: 10px"
      >
        <bk-table
          :size="'small'"
          :data="curRecord.resources"
          :header-cell-style="{ background: '#fafbfd', borderRight: 'none' }"
          ext-cls="paasng-expand-table"
        >
          <div slot="empty">
            <table-empty empty />
          </div>
          <bk-table-column
            prop="name"
            :label="$t('API名称')"
          />
          <bk-table-column
            prop="method"
            :label="$t('审批状态')"
          >
            <template slot-scope="prop">
              <template v-if="prop.row['apply_status'] === 'rejected'">
                <span class="paasng-icon paasng-reject" />
                {{ $t('驳回') }}
              </template>
              <template v-else-if="prop.row['apply_status'] === 'pending'">
                <round-loading ext-cls="applying" />
                {{ $t('待审批') }}
              </template>
              <template v-else>
                <span class="paasng-icon paasng-pass" />
                {{ prop.row['apply_status'] === 'approved' ? $t('通过') : $t('部分通过') }}
              </template>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
      <div
        v-else
        class="value"
      >
        {{ $t('网关下所有资源') }}
      </div>
    </div>
  </section>
</template>

<script>
export default {
  name: 'CloudApiDetail',
  props: {
    curRecord: {
      type: Object,
      default: () => {},
    },
    type: {
      type: String,
      default: 'component',
    },
  },
  data() {
    return {};
  },
  computed: {
    isComponentApi() {
      return this.type === 'component';
    },
    isEnglish() {
      return this.$store.state.localLanguage === 'en';
    },
  },
  methods: {
    getHandleBy(payload) {
      const list = payload?.filter((item) => !!item) || [];
      if (list.length < 1) {
        return '--';
      }
      return list.join('，');
    },
  },
};
</script>

<style lang="scss" scoped>
.paasng-kv-list {
  &.en {
    .item .key {
      min-width: 138px;
    }
  }
  .item {
    display: flex;
    font-size: 14px;
    min-height: 40px;
    line-height: 40px;

    &:last-child {
      border-bottom: none;
    }

    .key {
      min-width: 105px;
      padding-right: 24px;
      color: #63656e;
      text-align: right;
    }

    .value {
      color: #313238;
      flex: 1;
    }
  }
}
</style>
