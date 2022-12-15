<template>
  <div class="release-log-warp">
    <template v-if="logs.length">
      <pre
        v-for="(item, index) in logs"
        :key="index"
        class="log log-item pt10"
        v-html="item"
      />
    </template>
    <section
      v-else
      class="content"
    >
      <section>
        <div class="log-empty">
          {{ $t('暂无日志') }}
        </div>
      </section>
    </section>
  </div>
</template>
<script>
    export default {
        props: {
            log: {
                type: Array,
                default () {
                    return [];
                }
            }
        },
        data () {
            return {
                ansiUp: null
            };
        },
        computed: {
            logs () {
                if (this.ansiUp) {
                    return this.log.map(item => {
                        return this.ansiUp.ansi_to_html(item);
                    });
                }
                return this.log;
            }
        },
        watch: {
        },
        mounted () {
            // 初始化日志彩色组件
            // eslint-disable-next-line
            const AU = require('ansi_up')
            // eslint-disable-next-line
            this.ansiUp = new AU.default
        },
        methods: {
        }
    };
</script>

<style scoped lang="scss">
    .release-log-warp{
        padding: 17px 30px;
        width: calc(100% - 230px);
        height: calc(100vh - 272px);
        // height: 720px;
        background: #313238;
        overflow-y: auto;
        .log{
            font-size: 12px;
            color: #FFFFFF;
        }
        .content{
            position: relative;
            min-height: 60px;
            padding: 0 10px 10px 0;
            color: #fff;
            .log-empty {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 14px;
                color: #979ba5;
            }
        }
    }
</style>
