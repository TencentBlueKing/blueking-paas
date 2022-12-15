<template>
  <div class="container visible-range">
    <div class="app-container middle">
      <paas-plugin-title />
      <div class="desc mb20 mt10">
        仅可见范围内的组织、用户可在研发商店查看并使用该插件
      </div>
      <div class="group-warp mb20">
        <bk-button>选择组织/人员</bk-button>
        <div class="user-warp mt20">
          <div class="mb10">
            用户
          </div>
          <bk-tag
            closable
            @close="close"
          >
            企业邮箱
          </bk-tag>
        </div>
        <div class="organize-warp mt20">
          <div class="mb10">
            组织
          </div>
          <bk-tag
            closable
            @close="close"
          >
            企业邮箱
          </bk-tag>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
    import paasPluginTitle from '@/components/pass-plugin-title';
    export default {
        components: {
            paasPluginTitle
        },
        data () {
            return {};
        },
        watch: {

        },
        methods: {
            close () {}

        }
    };
</script>
<style lang="scss" scoped>
        .visible-range{
            .desc{
                font-size: 12px;
                color: #979BA5;
            }
        }
</style>
