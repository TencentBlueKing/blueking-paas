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
            v-html="currentLog"
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
      return marked(this.logList[this.active]?.detail || '');
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
        // const data = await this.$store.dispatch('getVersionLog');
        const data = [{"version":"V1.1.0","date":"2023-05-17","content":"# V1.1.0 版本更新日志\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n### 新增功能\n\n* 架构调整: workloads 服务合并至 apiserver\n- 支持云原生应用（需搭配 bkpaas-app-operator 使用）\n\n\n### 功能优化\n\n- Python 构建工具，默认 Python 版本为 3.10\n- 优化插件查询体验\n- 顶部导航样式修改\n- Python 构建工具中, python 版本的指定优先级 runtime.txt > 构建工具默认版本 > 缓存版本\n\n### 缺陷修复\n- 镜像凭证不能填写大于 255 个字符的问题\n- 概览页面、进程管理页面的报错问题\n- 日志查询的部分问题"},{"version":"V0.1.4","date":"2023-03-20","content":"# V0.1.4 版本更新日志\n### 新增功能\n- 支持 GitHub、Gitee OAuth 授权拉取代码\n- 提供 WebConsole 功能\n- 新增蓝鲸 APM 增强服务\n- 支持 IPV6\n- 支持 Redis 使用 sentinel 模式\n- 环境配置：显示内置环境变量\n- 初始化应用集群脚本支持设置容忍和污点\n- 应用权限迁移至权限中心\n\n### 缺陷修复\n- 创建 Smart 应用时应用名称未显示问题\n- 初始化集群，应用访问协议默认为 https 问题\n- 代码库管理无内容展示问题"},{"version":"V0.1.0","date":"2022-11-17","content":"# V0.1.0 版本更新日志\n### 新增功能\n- 全新设计的用户界面\n- 支持前后端分离的开发模式\n- 支持自定义后台进程及启动命令\n- 提供 MySQL、RabbitMQ、对象存储（bk-repo） 等增强服务\n- 支持通过镜像部署应用\n- 全面升级 Python 开发框架，并新增 Node.js 开发框架"}]
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
