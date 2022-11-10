<template functional>
    <div class="paas-deploy-log-skip-wrapper">
        <i class="paasng-icon paasng-exclamation-circle-shape"></i>
        {{ $t('未对蓝盾授权，无法执行，已跳过') }}
    </div>
</template>
<style lang="scss" scoped>
    .paas-deploy-log-skip-wrapper {
        padding-left: 19px;
        width: 100%;
        height: 50px;
        line-height: 50px;
        background: #2a2b2f;
        border-radius: 2px;
        font-size: 12px;
        color: #fff;
        i {
            margin-right: 5px;
            font-size: 14px;
            color: #63656e !important;
        }
    }
</style>
