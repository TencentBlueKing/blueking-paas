<template lang="html">
    <div class="paas-content white" data-test-id="create_content_App">
        <div class="big-title mt30">
            <span> {{ $t('创建应用') }} </span>
        </div>
        <div class="tab-box mt10" v-if="userFeature.ALLOW_CREATE_SMART_APP">
            <li :class="['tab-item', { 'active': appType === 'default' }, { 'tab-item-nosmart': !cloudFlag }]" @click="handleToggleType('default')"> {{ $t('普通应用') }} </li>
            <li :class="['tab-item', { 'active': appType === 'cloud' }, { 'tab-item-nosmart': !cloudFlag }]" @click="handleToggleType('cloud')" v-if="cloudFlag">{{ $t('云原生应用') }}</li>
            <li :class="['tab-item', { 'active': appType === 'smart' }, { 'tab-item-nosmart': !cloudFlag }]" @click="handleToggleType('smart')">{{ $t('S-mart 应用') }}</li>
            <li :class="['tab-item', { 'active': appType === 'external' }, { 'tab-item-nosmart': !cloudFlag }]" @click="handleToggleType('external')"> {{ $t('外链应用') }} </li>
        </div>
        <div class="tab-box mt10" v-else>
            <li :class="['tab-item tab-item-nosmart', { 'active': appType === 'default' }, { 'tab-item-nocloud': !cloudFlag }]" @click="handleToggleType('default')"> {{ $t('普通应用') }} </li>
            <li :class="['tab-item tab-item-nosmart', { 'active': appType === 'cloud' }, { 'tab-item-nocloud': !cloudFlag }]" @click="handleToggleType('cloud')" v-if="cloudFlag">{{ $t('云原生应用') }}</li>
            <li :class="['tab-item tab-item-nosmart', { 'active': appType === 'external' }, { 'tab-item-nocloud': !cloudFlag }]" @click="handleToggleType('external')"> {{ $t('外链应用') }} </li>
        </div>
        <create-default-app v-if="appType === 'default'" :key="appType"></create-default-app>
        <create-cloud-app v-else-if="appType === 'cloud'" key="cloud"></create-cloud-app>
        <create-external-app v-else-if="appType === 'external'" key="external"></create-external-app>
        <create-smart-app v-else key="smart"></create-smart-app>
    </div>
</template>

<script>
    import createDefaultApp from './default';
    import createSmartApp from './smart';
    import createExternalApp from './external';
    import createCloudApp from './cloud';

    const queryMap = {
        default: 'app',
        cloud: 'cloudNativeApp',
        smart: 'smartApp',
        external: 'externalApp'
    };

    export default {
        components: {
            createDefaultApp,
            createSmartApp,
            createExternalApp,
            createCloudApp
        },
        data () {
            return {
                appType: 'default'
            };
        },
        computed: {
            userFeature () {
                return this.$store.state.userFeature;
            },
            cloudFlag () {
                if (this.$store.state.userFeature) {
                    return this.$store.state.userFeature.ALLOW_CREATE_CLOUD_NATIVE_APP;
                }
                return false;
            },
            searchQuery () {
                return this.$route.query;
            }
        },
        created () {
            this.switchAppType();
        },
        methods: {
            handleToggleType (type) {
                if (this.searchQuery.type) {
                    const query = JSON.parse(JSON.stringify(this.searchQuery));
                    query.type = queryMap[type];
                    this.$router.push({ path: this.$route.path, query });
                }
                if (this.appType === type) {
                    return false;
                }
                this.appType = type;
            },
            switchAppType () {
                if (this.searchQuery.type) {
                    switch (this.searchQuery.type) {
                        case 'cloudNativeApp':
                            this.appType = 'cloud';
                            break;
                        case 'smartApp':
                            this.appType = 'smart';
                            break;
                        case 'externalApp':
                            this.appType = 'external';
                            break;
                        default:
                            this.appType = 'default';
                            break;
                    }
                }
            }
        }
    };
</script>

<style lang="scss" scoped>
    .tab-box {
        width: 1000px;
        margin: auto;
        height: 56px;
        list-style: none;
        display: flex;
        justify-content: space-between;

        .tab-item {
            width: 240px;
            height: 56px;
            line-height: 56px;
            text-align: center;
            background: #f0f1f5;
            border-radius: 2px;
            font-size: 14px;
            color: #63656e;
            cursor: pointer;
            position: relative;

            &.active {
                background: #fff;
                border: 2px solid #3a84ff;
                color: #3a84ff;

                &::after {
                    width: 16px;
                    height: 16px;
                    border: 2px solid #fff;
                    border-radius: 50%;
                    content: "\e157";
                    font-family: 'paasng' !important;
                    font-size: 12px;
                    position: absolute;
                    right: -8px;
                    top: -8px;
                    line-height: 1;
                    display: inline-block;
                    z-index: 10;
                    background: #fff;
                }
            }
        }
        .tab-item-nosmart{
           width: 328px;
        }
        .tab-item-nocloud{
            width: 490px;
        }
    }

    .big-title {
        padding: 15px 0 11px 0;
        color: #666;
        line-height: 36px;
        position: relative;
        position: relative;
        line-height: 34px;
        text-align: center;
        font-weight: 700;

        &::before,
        &::after {
            content: "";
            position: absolute;
            width: 528px;
            height: 1px;
            background: #e9edee;
            left: 0;
            top: 32px;
        }

        &::after {
            left: auto;
            right: 0
        }

        & span {
            display: inline-block;
            padding: 0 24px;
            background: #fff;
            line-height: 34px;
            font-size: 18px;
            color: #333;
            z-index: 9;
        }
    }
</style>
