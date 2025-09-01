<template lang="html">
  <div
    class="fright-middle fright-last"
    data-test-id="summary_content_noSource"
  >
    <h3>{{ $t('最新动态') }}</h3>
    <ul class="dynamic-list">
      <template v-if="operationsList.length">
        <li
          v-for="(item, itemIndex) in operationsList"
          :key="itemIndex"
        >
          <p class="dynamic-time">
            <span
              v-bk-tooltips="item.at"
              class="tooltip-time"
            >
              {{ item.at_friendly }}
            </span>
          </p>
          <p class="dynamic-content">
            <span v-if="isMultiTenantDisplayMode">
              <bk-user-display-name :user-id="item.operator"></bk-user-display-name>
              {{ formattedOperate(item.operate) }}
            </span>
            <template v-else>{{ item.operate }}</template>
          </p>
        </li>
        <li />
      </template>
      <template v-else>
        <table-empty empty />
      </template>
    </ul>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
  props: {
    operationsList: {
      type: Array,
      default: () => [],
    },
  },
  computed: {
    ...mapGetters(['isMultiTenantDisplayMode']),
    curAppInfo() {
      return this.$store.state.curAppInfo;
    },
    isEngineless() {
      return this.curAppInfo.web_config.engine_enabled;
    },
  },
  methods: {
    formattedOperate(operate) {
      return operate ? operate.split(' ').slice(1).join(' ') : '';
    },
  },
};
</script>

<style lang="scss" scoped>
.dynamic-list li {
  padding-bottom: 15px;
  padding-left: 20px;
  position: relative;
}

.dynamic-list li:before {
  position: absolute;
  content: '';
  width: 10px;
  height: 10px;
  top: 3px;
  left: 1px;
  border: solid 1px rgba(87, 163, 241, 1);
  border-radius: 50%;
}

.dynamic-list li:after {
  position: absolute;
  content: '';
  width: 1px;
  height: 70px;
  top: 15px;
  left: 6px;
  background: rgba(87, 163, 241, 1);
}

$a: 10;
@for $i from 1 through 10 {
  $step: ($a - $i + 1) / 10;
  @if $step <= 0.2 {
    $step: 0.2;
  }
  .dynamic-list li:nth-child(#{$i}):before {
    border: solid 1px rgba(87, 163, 241, $step);
  }
  .dynamic-list li:nth-child(#{$i}):after {
    background: rgba(87, 163, 241, $step);
  }
}

.dynamic-list li:last-child:before {
  border: solid 1px rgba(87, 163, 241, 0.2);
}

.dynamic-list li:last-child:after {
  background: rgba(87, 163, 241, 0);
}

.dynamic-time {
  line-height: 18px;
  font-size: 12px;
  color: #c0c9d3;
  cursor: default;
}

.dynamic-content {
  line-height: 24px;
  height: 48px;
  overflow: hidden;
  color: #666;
}
</style>
