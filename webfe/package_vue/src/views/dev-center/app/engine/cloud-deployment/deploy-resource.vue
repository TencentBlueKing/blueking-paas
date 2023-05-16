<template>
  <paas-content-loader
    :is-loading="isLoading"
    placeholder="deploy-resource-loading"
    :offset-top="20"
    :offset-left="20"
    class="deploy-action-box"
  >
    <div class="resource-contanier">
      <div class="resource-item mb20">
        <div class="pb10">
          <span class="item-title">{{ $t('增强服务') }}</span>
          <router-link
            :to="{ path: `/developer-center/apps/${appCode}/default/service/1` }"
            class="link pl20"
          >
            {{ $t('管理增强服务') }}
          </router-link>
        </div>
        <div class="item-data">
          {{ $t('启用未创建') }}: {{ notCreated || $t('无') }}
        </div>
        <div class="item-data">
          {{ $t('已创建实例') }}: {{ created || $t('无') }}
        </div>
      </div>
      <div class="resource-item no-border">
        <div class="item-title-content">
          <span class="item-title pb10">
            {{ $t('服务发现') }}
          </span>
          <span>{{ $t('（其他 SaaS）') }}</span>
        </div>
        <div class="item-data">
          {{ $t('通过环境变量获取其他Saas应用的访问地址') }}
          <a
            target="_blank"
            :href="GLOBAL.DOC.SERVE_DISCOVERY"
            style="color: #3a84ff"
          >{{ $t('查看使用帮助') }}</a>
        </div>
      </div>
    </div>
  </paas-content-loader>
</template>
<script>
    import appBaseMixin from '@/mixins/app-base-mixin.js';
    import { uniqBy } from 'lodash';
    export default {
        mixins: [appBaseMixin],
        data () {
            return {
                resourceData: {
                    notCreated: [],
                    created: []
                },
                notCreated: [],
                created: [],
                isLoading: true
            };
        },
        watch: {
            resourceData: {
                handler (value) {
                    this.notCreated = value.notCreated && value.notCreated.map(e => e.display_name).join('，');
                    this.created = value.created && value.created.map(e => e.display_name).join('，');
                },
                immediate: true,
                deep: true
            }
        },
        mounted () {
            this.getCloudAppServicesInfo();
        },
        methods: {
            async getCloudAppServicesInfo () {
                try {
                    const res = await this.$store.dispatch('deploy/getCloudAppResource', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId
                    });

                    // 启用未创建数据
                    this.resourceData = Object.keys(res).reduce((p, e) => {
                        const notCreatedData = res[e].filter(item => !item.is_provisioned);
                        const createdData = res[e].filter(item => item.is_provisioned);
                        p.notCreated.push(...notCreatedData);
                        p.created.push(...createdData);
                        return p;
                    }, { notCreated: [], created: [] });

                    // 已创建实例

                    this.resourceData.notCreated = uniqBy(this.resourceData.notCreated, 'name'); // 根据name去重
                    this.resourceData.created = uniqBy(this.resourceData.created, 'name'); // 根据name去重
                    // 若 prod 对应分类不存在该服务，则展示（带上测试的备注）
                    this.resourceData.created.map(e => {
                        if (!res['prod'].find(item => item.name === e.name)) {
                            e.display_name = e.display_name + '(测试)';
                        } else {
                            res['prod'].forEach(element => {
                                if ((e.name === element.name && !element.is_provisioned)) {
                                    e.display_name = e.display_name + '(测试)';
                                }
                            });
                        }
                        return e;
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || e.message
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 500);
                }
            },

            formDataValidate (index) {
                if (index) {
                    return false;
                }
            }
        }
    };
</script>
<style lang="scss">
    .resource-contanier{
        padding: 20px;
        .resource-item{
            padding-bottom: 20px;
            border-bottom: 1px solid #DCDEE5;
            .item-title{
                font-weight: Bold;
                font-size: 14px;
                color: #313238;
            }
            .item-data{
                padding: 10px 30px;
            }
        }
        .no-border{
            border-bottom: none;
        }
    }
</style>
