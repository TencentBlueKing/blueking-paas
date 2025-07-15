<template lang="html">
  <service-general
    class="frame-wrapper"
    :data="apiData"
  />
</template>

<script>
    import serviceGeneral from '@/components/serviceGeneral';
    export default {
        components: {
            serviceGeneral
        },
        data () {
            const appList = [
                {
                    'title': `Python ${this.$t('开发框架（blueapps）')}`,
                    'explain': `Python ${this.$t('开发框架基于 Django 开发，集成用户鉴权、应用日志等基础功能。')}`,
                    'action_links': [
                        {
                            'text': this.$t('框架文档'),
                            'target_url': this.GLOBAL.DOC.PYTHON_FRAMEWORK
                        }
                    ]
                }
            ];
            if (this.GLOBAL.CONFIG.GO_FRAME) {
                appList.push({
                    'title': `Go ${this.$t('开发框架')}`,
                    'explain': `Go  ${this.$t('开发框架在 Gin 基础上，集成用户登录、蓝鲸组件调用和其他增强服务。')}`,
                    'action_links': [
                        {
                            'text': this.$t('快速开始'),
                            'target_url': this.GLOBAL.DOC.GO_START
                        }
                    ]
                });
            }
            appList.push(
                {
                    'title': `NodeJS ${this.$t('开发框架')}`,
                    'explain': `NodeJS ${this.$t('开发框架，集成蓝鲸 Vue 组件库、统一登录和其他开发示例。')}`,
                    'action_links': [
                        {
                            'text': this.$t('快速开始'),
                            'target_url': this.GLOBAL.DOC.NODE_FRAMEWORK
                        }
                    ]
                },
                {
                    'title': this.$t('其他开发资料'),
                    'explain': '',
                    'action_links': [
                        {
                            'text': `Python ${this.$t('开发规范')}`,
                            'target_url': this.GLOBAL.DOC.PTTHON_DEV_GUIDE

                        },
                        {
                            'text': this.$t('前端开发规范'),
                            'target_url': this.GLOBAL.DOC.FRONTEND_DEV_GUIDE
                        },
                        {
                            'text': this.$t('开发者常见问题'),
                            'target_url': this.GLOBAL.DOC.FAQ
                        },
                        {
                            'text': this.$t('结合前端BKUI-CLI使用指南'),
                            'target_url': this.GLOBAL.DOC.BKUI_WITH_PYTHON
                        }
                    ]
                }
            );
            return {
                apiData: {
                    name: this.$t('开发框架'),
                    apititle: this.$t('蓝鲸应用开发框架'),
                    image: '/static/images/service-pic10.png',
                    apiexplain: this.$t('蓝鲸应用开发框架为开发者提供统一登录鉴权、敏感权限、功能开关、权限控制、日志、查询组件、常用tags等基础功能模块，以及CRUD、云API调用、任务调度、后台任务等样例，助力开发者快速上手开发蓝鲸应用'),
                    apiList: appList
                }
            };
        }
    };
</script>

<style media="screen" lang="scss" scoped>
    .paasng-angle-double-right {
        padding-left: 3px;
        font-size: 12px;
        font-weight: bold;
    }
</style>
