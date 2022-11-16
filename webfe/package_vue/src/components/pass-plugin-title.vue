<template>
  <div class="plugin-top-title">
    <div class="title-container flex-row align-items-center">
      <i
        v-if="showBackIcon"
        class="paasng-icon paasng-arrows-left icon-cls-back mr5"
        @click="goBack"
      />
      <div class="title">
        {{ title }}
        <span v-if="version">{{ version }}</span>
      </div>
    </div>
  </div>
</template>
<script>
    export default {
        props: {
            name: {
                type: String,
                default () {
                    return '';
                }
            },
            version: {
                type: String,
                default () {
                    return '';
                }
            }
        },
        data () {
            return {
                showBackIcon: false
            };
        },
        watch: {
            '$route': {
                handler (value) {
                    if (value) {
                        this.title = this.name || (value.meta && value.meta.pathName);
                        this.showBackIcon = value.meta && value.meta.supportBack;
                    }
                },
                immediate: true
            }
        },
        methods: {
            goBack () {
                this.$router.go(-1);
            }
        }
    };
</script>
<style lang="scss" scoped>
    .plugin-top-title{
        .title-container{
            .title{
                font-size: 16px;
                color: #313238;
                letter-spacing: 0;
                line-height: 24px;
            }
            .icon-cls-back{
                color: #3A84FF;
                font-size: 20px;
                font-weight: bold;
                cursor: pointer;
            }
        }
    }
</style>
