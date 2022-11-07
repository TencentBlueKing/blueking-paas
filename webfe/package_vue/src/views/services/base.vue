<template lang="html">
    <div class="overview-content">
        <div class="wrap">
            <div class="overview">
                <div class="overview-main" :style="{ 'min-height': `${minHeight}px` }">
                    <div class="overview-fleft">
                        <div class="overview-tit">
                            <div class="title service-title">
                                <img src="/static/images/service-pic1.png" class="overview-title-pic fleft">
                                <span class="overview-title-text f16"> {{ $t('服务') }} </span>
                            </div>
                        </div>
                        <paasNav :nav-categories="navCategories" :nav-items="navItems"></paasNav>
                    </div>
                    <div class="overview-fright">
                        <router-view></router-view>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
    import paasNav from '@/components/paasNav';
    import { processNavData } from '@/common/utils';
    import { psServiceNavInfo } from '@/mixins/ps-static-mixin';

    export default {
        components: {
            'paasNav': paasNav
        },
        mixins: [psServiceNavInfo],
        data () {
            return {
                minHeight: 700,
                navCategories: [],
                navItems: []
            };
        },
        mounted () {
            const resData = this.serviceNavStaticInfo.list;
            const result = processNavData(resData);
            this.navCategories = result.navCategories;
            this.navItems = result.navItems;

            const HEADER_HEIGHT = 50;
            const FOOTER_HEIGHT = 0;
            const winHeight = window.innerHeight;
            const contentHeight = winHeight - HEADER_HEIGHT - FOOTER_HEIGHT;
            if (contentHeight > this.minHeight) {
                this.minHeight = contentHeight;
            }
            document.body.className = 'ps-service-detail';
        },
        
        beforeDestroy () {
            document.body.className = '';
        }
    };

</script>

<style lang="scss" scoped>
    .service-title {
        line-height: 50px;
    }

    .service-title .overview-title-pic {
        margin: 14px 14px 10px 20px;
        height: auto;
    }
</style>
