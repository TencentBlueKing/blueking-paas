<template lang="html">
    <!-- loading true时显示loading -->
    <div class="paas-loading-content">
        <slot v-if="loading">
            <div class="paas-loading-panel">
                <div class="text">
                    <div class="bk-loading1">
                        <div class="point point1"></div>
                        <div class="point point2"></div>
                        <div class="point point3"></div>
                        <div class="point point4"></div>
                    </div>
                </div>
            </div>
        </slot>
        <slot name="loadingContent" v-else></slot>
    </div>

</template>

<script>

    export default {
        props: {
            loading: {
                type: Boolean
            }
        }
    };
</script>

<style lang="scss">

</style>
