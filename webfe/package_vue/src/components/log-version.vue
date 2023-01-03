<template>
  <bk-dialog
    width="1105"
    :value="show"
    :show-footer="false"
    @value-change="handleValueChange"
  >
    <template>
      <div
        v-bkloading="{ isLoading: loading }"
        class="log-version"
      >
        <div class="log-version-left">
          <ul class="left-list">
            <li
              v-for="(item, index) in logList"
              :key="index"
              class="left-list-item"
              :class="{ 'item-active': index === active }"
              @click="handleItemClick(index)"
            >
              <span class="item-title">{{ item.title }}</span>
              <span class="item-date">{{ item.date }}</span>
              <span
                v-if="index === current"
                class="item-current"
              >{{ $t('当前版本') }}</span>
            </li>
          </ul>
        </div>
        <div
          v-bkloading="{ isLoading: contactLoading, zIndex: 10 }"
          class="log-version-right"
        >
          <!-- eslint-disable vue/no-v-html -->
          <div
            class="detail-container"
            v-html="currentLog.detail"
          />
          <!--eslint-enable-->
        </div>
      </div>
    </template>
  </bk-dialog>
</template>

<script>
export default {
  name: 'LogVersion',
  props: {
    dialogShow: Boolean
  },
  data () {
    return {
      show: false,
      current: 0,
      active: 0,
      logList: [],
      loading: false,
      contactLoading: false
    };
  },
  computed: {
    currentLog () {
      return this.logList[this.active] || {};
    }
  },
  watch: {
    dialogShow: {
      async handler (v) {
        this.show = v;
        if (v) {
          this.loading = true;
          this.logList = await this.getVersionLogsList();
          if (this.logList.length) {
            await this.handleItemClick();
          }
          this.loading = false;
        }
      },
      immediate: true
    }
  },
  beforeDestroy () {
    this.show = false;
    this.$emit('update:dialogShow', false);
  },
  methods: {
    handleValueChange (v) {
      this.$emit('update:dialogShow', v);
    },
    // 查看log详情
    async handleItemClick (index = 0, curEvent) {
      this.loading = true;
      this.active = index;
      setTimeout(() => {
        this.loading = false;
      }, 20);
    },
    async getVersionLogsList () {
      try {
        const data = await this.$store.dispatch('getVersionLog');
        return data.map(item => ({ title: item.version, date: item.date, detail: item.content }));
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常')
        });
      }
    }
  }
};
</script>

<style lang="scss" scoped>
  .log-version {
    display: flex;
    margin: -33px -24px -26px;

    &-left {
      flex: 0 0 180px;
      background-color: #fafbfd;
      border-right: 1px solid #dcdee5;
      padding: 40px 0;
      display: flex;
      font-size: 12px;

      .left-list {
        border-top: 1px solid #dcdee5;
        border-bottom: 1px solid #dcdee5;
        height: 520px;
        overflow: auto;
        display: flex;
        flex-direction: column;
        width: 100%;

        &-item {
          flex: 0 0 54px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding-left: 30px;
          position: relative;
          border-bottom: 1px solid #dcdee5;

          &:hover {
            cursor: pointer;
            background-color: #fff;
          }

          .item-title {
            color: #313238;
            font-size: 16px;
          }

          .item-date {
            color: #979ba5;
          }

          .item-current {
            position: absolute;
            right: 20px;
            top: 8px;
            background-color: #699df4;
            border-radius: 2px;
            width: 58px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
          }

          &.item-active {
            background-color: #fff;

            &::before {
              content: '';
              position: absolute;
              top: 0px;
              bottom: 0px;
              left: 0;
              width: 6px;
              background-color: #3a84ff;
            }
          }
        }
      }
    }

    &-right {
      flex: 1;
      padding: 25px 30px 50px 45px;

      .detail-container {
        max-height: 525px;
        overflow: auto;
      }
    }
  }
</style>
