<template>
    <content-loader
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})`, 'margin-top': '10px' }"
        :width="baseWidth"
        :height="360"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <!-- <path d="M 200 254 c 0.6 0 1 0.4 1 1 v 14 c 0 0.6 -0.4 1 -1 1 H 1 c -0.6 0 -1 -0.4 -1 -1 v -14 c 0 -0.6 0.4 -1 1 -1 h 199 z m 0 -36 c 0.6 0 1 0.4 1 1 v 14 c 0 0.6 -0.4 1 -1 1 H 1 c -0.6 0 -1 -0.4 -1 -1 v -14 c 0 -0.6 0.4 -1 1 -1 h 199 z m 121 -36 c 0.6 0 1 0.4 1 1 v 14 c 0 0.6 -0.4 1 -1 1 H 1 c -0.6 0 -1 -0.4 -1 -1 v -14 c 0 -0.6 0.4 -1 1 -1 h 320 z m 147 -40 c 0.6 0 1 0.4 1 1 v 14 c 0 0.6 -0.4 1 -1 1 H 1 c -0.6 0 -1 -0.4 -1 -1 v -14 c 0 -0.6 0.4 -1 1 -1 h 467 z m 710 -93 c 1.1 0 2 0.9 2 2 v 71 c 0 1.1 -0.9 2 -2 2 H 2 c -1.1 0 -2 -0.9 -2 -2 V 51 c 0 -1.1 0.9 -2 2 -2 h 1176 z m 2 -21 v 1 H 0 v -1 h 1180 z M 73 0 c 0.6 0 1 0.4 1 1 v 14 c 0 0.6 -0.4 1 -1 1 H 1 c -0.6 0 -1 -0.4 -1 -1 V 1 c 0 -0.6 0.4 -1 1 -1 h 72 z m 98 0 c 0.6 0 1 0.4 1 1 v 14 c 0 0.6 -0.4 1 -1 1 H 99 c -0.6 0 -1 -0.4 -1 -1 V 1 c 0 -0.6 0.4 -1 1 -1 h 72 z" /> -->
        <rect x="0" y="0" rx="0" ry="2" width="100" height="32" />
        <rect x="0" y="58" rx="2" ry="2" :width="baseWidth" height="82" />
        <!-- <path d="M 0 28 h 1180 v 1 H 0 z" /> -->
    </content-loader>
</template>

<script>
    import { ContentLoader } from 'vue-content-loader';
    export default {
        components: {
            ContentLoader
        },
        props: {
            baseWidth: {
                type: Number,
                default: 1180
            },
            contentWidth: {
                type: Number,
                default: 1180
            }
        },
        computed: {
            loadingConf () {
                return this.$store.state.loadingConf;
            }
        }
    };
</script>
