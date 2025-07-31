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
              >{{ $t('当前版本-label') }}</span>
            </li>
          </ul>
        </div>
        <div
          v-bkloading="{ isLoading: contactLoading, zIndex: 10 }"
          class="log-version-right"
        >
          <div
            class="detail-container"
            v-dompurify-html="currentLog"
          />
          <!--eslint-enable-->
        </div>
      </div>
    </template>
  </bk-dialog>
</template>

<script>
import { marked } from 'marked';
export default {
  name: 'LogVersion',
  props: {
    dialogShow: Boolean,
  },
  data() {
    return {
      show: false,
      current: 0,
      active: 0,
      logList: [],
      loading: false,
      contactLoading: false,
    };
  },
  computed: {
    currentLog() {
      return marked(this.logList[this.active]?.detail || '');
    },
  },
  watch: {
    dialogShow: {
      async handler(v) {
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
      immediate: true,
    },
  },
  beforeDestroy() {
    this.show = false;
    this.$emit('update:dialogShow', false);
  },
  methods: {
    handleValueChange(v) {
      this.$emit('update:dialogShow', v);
    },
    // 查看log详情
    async handleItemClick(index = 0, curEvent) {
      this.loading = true;
      this.active = index;
      setTimeout(() => {
        this.loading = false;
      }, 20);
    },
    async getVersionLogsList() {
      try {
        const data = await this.$store.dispatch('getVersionLog');
        return data.map(item => ({ title: item.version, date: item.date, detail: item.content }));
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      }
    },
  },
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
<style lang="scss">
.detail-container{

  font-size: 14px;
        color: #313238;
        h1,
        h2,
        h3,
        h4,
        h5 {
            margin: 10px 0;
            font: normal 14px/1.5 "Helvetica Neue",Helvetica Neue,Helvetica,Arial,Lantinghei SC,Hiragino Sans GB,Microsoft Yahei,sans-serif;
            color: #34383e;
            height: auto;
            font-weight: bold;
        }
        h1 {
            font-size: 30px
        }

        h2 {
            font-size: 24px
        }

        h3 {
            font-size: 18px
        }

        h4 {
            font-size: 16px
        }

        h5 {
            font-size: 14px
        }

        em {
            font-style: italic
        }

        div,p,font,span,li {
            line-height: 1.3
        }

        p {
            margin: 0 0 1em
        }

        table,table p {
            margin: 0
        }

        ul,ol {
            padding: 0;
            margin: 0 0 1em 2em;
            text-indent: 0
        }

        ul {
            padding: 0;
            margin: 10px 0 10px 15px;
            list-style-type: none
        }

        ol {
            padding: 0;
            margin: 10px 0 10px 25px
        }

        ol>li {
            white-space: normal;
            line-height: 1.8
        }

        ul>li {
            white-space: normal;
            padding-left: 15px !important;
            line-height: 1.8;
            &:before{
                content: '';
                display: inline-block;
                width: 6px;
                height: 6px;
                margin-right: 9px;
                margin-left: -15px;
                border-radius: 50%;
                background: #000;
            }
        }

        li>ul {
            margin-bottom: 10px
        }

        li ol {
            padding-left: 20px !important
        }

        ul ul,ul ol,ol ol,ol ul {
            margin-bottom: 0;
            margin-left: 20px
        }

        ul.list-type-1>li {
            list-style: circle !important;
            padding-left: 0 !important;
            margin-left: 15px !important;
            background: none !important
        }

        ul.list-type-2>li {
            list-style: square !important;
            padding-left: 0 !important;
            margin-left: 15px !important;
            background: none !important
        }

        ol.list-type-1>li {
            list-style: lower-greek !important
        }

        ol.list-type-2>li {
            list-style: upper-roman !important
        }

        ol.list-type-3>li {
            list-style: cjk-ideographic !important
        }

        pre,code {
            padding: 0 3px 2px;
            font-family: Monaco,Menlo,Consolas,"Courier New",monospace;
            font-size: 14px;
            color: #333;
            -webkit-border-radius: 3px;
            -moz-border-radius: 3px;
            border-radius: 3px;
            width: 95%
        }

        code {
            font-family: Consolas,monospace,tahoma,Arial;
            padding: 2px 4px;
            color: #d14;
            border: 1px solid #e1e1e8
        }

        pre {
            font-family: Consolas,monospace,tahoma,Arial;
            display: block;
            padding: 9.5px;
            margin: 0 0 10px;
            font-size: 13px;
            word-break: break-all;
            word-wrap: break-word;
            white-space: pre-wrap;
            background-color: #f6f6f6;
            border: 1px solid #ddd;
            border: 1px solid rgba(0,0,0,0.15);
            border-radius: 2px
        }

        pre code {
            padding: 0;
            white-space: pre-wrap;
            border: 0
        }
}
</style>
