<template lang="html">
  <div class="container biz-create-success">
    <div class="success-wrapper">
      <div class="info">
        <p>
          <i class="paasng-icon paasng-check-circle-shape text-success" />
        </p>
        <p>{{ $t('恭喜，应用') }}&nbsp;&nbsp;"{{ application.name }}"&nbsp;&nbsp;{{ $t('创建成功') }}</p>
        <p v-if="application.type === 'cloud_native'">
          {{ $t('常用操作：') }}
          <router-link
            :to="{ name: 'cloudAppDeploy', params: { id: appCode } }"
            class="link"
          >
            {{ $t('应用编排') }}
          </router-link>
          <span class="success-dividing-line">|</span>
          <router-link
            :to="{ name: 'appRoles', params: { id: appCode } }"
            class="link"
          >
            {{ $t('成员管理') }}
          </router-link>
        </p>
        <p v-else>
          {{ $t('常用操作：') }}
          <router-link
            :to="{ name: 'appRoles', params: { id: appCode } }"
            class="link"
          >
            {{ $t('添加成员') }}
          </router-link>
          <span class="success-dividing-line">|</span>
          <router-link
            :to="{ name: 'appCloudAPI', params: { id: appCode } }"
            class="link"
          >
            {{ $t('云API申请') }}
          </router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script>
    export default {
        data () {
            const appCode = this.$route.params.id;
            return {
                appCode: appCode,
                application: {}
            };
        },
        created () {
            const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/`;
            this.$http.get(url).then((response) => {
                const body = response;
                this.application = body.application;
            });
        }
    };
</script>

<style lang="scss" scoped>
    .biz-create-success {
        padding: 120px 0 20px 0;
    }
    .success-wrapper {
        width: 100%;
        height: 245px;
        border: 1px solid #dcdee5;
        border-radius: 2px;
        .info {
            padding-top: 45px;
            height: 200px;
            p:nth-child(1) {
                text-align: center;
                .text-success {
                    font-size: 49px;
                    color: #2dcb56;
                }
            }
            p:nth-child(2) {
                margin-top: 16px;
                font-size: 16px;
                font-weight: bold;
                color: #313238;
                text-align: center;
            }
            p:nth-child(3) {
                margin-top: 12px;
                font-size: 14px;
                color: #63656e;
                text-align: center;
                .link {
                    color: #3a84ff;
                    cursor: pointer;
                    &:hover {
                        color: #699df4;
                    }
                }
            }
        }
    }
</style>
