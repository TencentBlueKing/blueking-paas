<template>
  <div :class="['paas-deploy-log-stage-wrapper', extCls]">
    <label
      v-if="isShowTitle"
      class="title"
    >{{ title }}</label>
    <section class="content-wrapper">
      <section
        ref="content"
        class="content"
      >
        <p
          v-for="(item, index) in logs"
          :key="index"
          class="log-item"
        >
          <span v-dompurify-html="item.timestamp" />
          <span
            style="margin-left: 25px;"
            v-dompurify-html="item.message"
          />
        </p>
      </section>
      <div
        v-if="isShowFullScreen"
        class="screen-wrapper"
        @click.stop="handleFullScreen"
      >
        <i class="paasng-icon paasng-full-screen-new" />
      </div>
    </section>

    <bk-dialog
      v-model="fullDialogVisiable"
      fullscreen
      :show-footer="false"
      ext-cls="paas-deploy-log-full-screen-cls"
      title=""
    >
      <div
        class="screen-icon-wrapper"
        @click="fullDialogVisiable = false"
      >
        <i class="paasng-icon paasng-restore-screen" />
      </div>
      <div
        ref="dialogContent"
        class="dialog-log-content"
      >
        <p
          v-for="(item, index) in logs"
          :key="index"
          class="log-item"
        >
          <span v-dompurify-html="item.timestamp" />
          <span
            style="margin-left: 25px;"
            v-dompurify-html="item.message"
          />
        </p>
      </div>
    </bk-dialog>
  </div>
</template>
<script>
    export default {
        name: '',
        props: {
            title: {
                type: String,
                default: ''
            },
            data: {
                type: Array,
                default: () => []
            },
            canFullScreen: {
                type: Boolean,
                default: false
            },
            extCls: {
                type: String,
                default: ''
            }
        },
        data () {
            return {
                fullDialogVisiable: false,
                logs: this.data
            };
        },
        computed: {
            isShowFullScreen () {
                return this.canFullScreen && this.logs.length > 0;
            },
            isShowTitle () {
                return this.title !== '';
            }
        },
        watch: {
            data: {
                handler (value) {
                    this.logs = value;
                }
            }
        },
        methods: {
            handleScrollToBottom () {
                this.$refs.content.scrollTop = this.$refs.content.scrollHeight;
                if (this.fullDialogVisiable) {
                    this.$refs.dialogContent.scrollTop = this.$refs.dialogContent.scrollHeight;
                }
            },
            handleFullScreen () {
                this.fullDialogVisiable = true;
                this.$refs.dialogContent.scrollTop = this.$refs.dialogContent.scrollHeight;
            }
        }
    };
</script>
<style lang="scss" scoped>
    .paas-deploy-log-stage-wrapper {
        .title {
            display: inline-block;
            margin-bottom: 8px;
            font-size: 14px;
            color: #979ba5;
        }
        .content-wrapper {
            position: relative;
            width: 100%;
            min-height: 60px;
            background: #2a2b2f;
            border-radius: 2px;
            .screen-wrapper {
                position: absolute;
                top: 15px;
                right: 20px;
                cursor: pointer;
                i {
                    font-size: 16px;
                    color: #63656e;
                }
            }
        }
        .content {
            padding: 15px 20px;
            width: 100%;
            // max-height: 500px;
            overflow-y: auto;
            &::-webkit-scrollbar {
                width: 4px;
                background-color: lighten(transparent, 80%);
            }
            &::-webkit-scrollbar-thumb {
                height: 5px;
                border-radius: 2px;
                background-color: #63656e;
            }
            .log-item {
                display: flex;
                justify-content: flex-start;
                line-height: 20px;
                font-size: 12px;
                color: #c4c6cc;
                font-family: Consolas,source code pro,Bitstream Vera Sans Mono,Courier,monospace,\\5FAE\8F6F\96C5\9ED1,Arial;
            }
        }
    }

    .paas-deploy-log-full-screen-cls {
        .screen-icon-wrapper {
            position: absolute;
            top: 10px;
            right: 10px;
            cursor: pointer;
            i {
                font-size: 18px;
                color: #63656e;
            }
        }
        .dialog-log-content {
            padding: 15px 20px;
            max-height: 100vh;
            overflow-y: auto;
            &::-webkit-scrollbar {
                width: 4px;
                background-color: lighten(transparent, 80%);
            }
            &::-webkit-scrollbar-thumb {
                height: 5px;
                border-radius: 2px;
                background-color: #63656e;
            }
            .log-item {
                display: flex;
                justify-content: flex-start;
                line-height: 20px;
                font-size: 12px;
                color: #c4c6cc;
                font-family: Consolas,source code pro,Bitstream Vera Sans Mono,Courier,monospace,\\5FAE\8F6F\96C5\9ED1,Arial;
            }
        }
    }
</style>
