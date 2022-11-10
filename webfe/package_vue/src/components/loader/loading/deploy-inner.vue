<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="610"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="2" y="53" rx="1" ry="1" width="170" height="16" /> 
        <rect x="320" y="166" rx="2" ry="2" width="880" height="447" /> 
        <rect x="2" y="1" rx="2" ry="2" width="1140" height="38" /> 
        <rect x="2" y="78" rx="2" ry="2" width="560" height="42" /> 
        <rect x="582" y="78" rx="2" ry="2" width="560" height="42" /> 
        <circle cx="15" cy="191" r="8" /> 
        <circle cx="15" cy="351" r="8" /> 
        <circle cx="15" cy="511" r="8" /> 
        <circle cx="15" cy="228" r="5" /> 
        <circle cx="14" cy="388" r="5" /> 
        <circle cx="14" cy="428" r="5" /> 
        <circle cx="14" cy="548" r="5" /> 
        <circle cx="14" cy="588" r="5" /> 
        <circle cx="14" cy="468" r="5" /> 
        <circle cx="15" cy="268" r="5" /> 
        <circle cx="15" cy="308" r="5" /> 
        <path d="M 30.5 384.781 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 V 771 h 1 v -2.219 h -1 z" /> 
        <rect x="27" y="183" rx="2" ry="2" width="56" height="16" /> 
        <rect x="27" y="343" rx="2" ry="2" width="56" height="16" /> 
        <rect x="27" y="503" rx="2" ry="2" width="56" height="16" /> 
        <rect x="27" y="541" rx="2" ry="2" width="113" height="16" /> 
        <rect x="27" y="581" rx="2" ry="2" width="113" height="16" /> 
        <rect x="27" y="381" rx="2" ry="2" width="113" height="16" /> 
        <rect x="27" y="421" rx="2" ry="2" width="113" height="16" /> 
        <rect x="27" y="461" rx="2" ry="2" width="113" height="16" /> 
        <rect x="27" y="221" rx="2" ry="2" width="113" height="16" /> 
        <rect x="27" y="261" rx="2" ry="2" width="113" height="16" /> 
        <rect x="27" y="301" rx="2" ry="2" width="113" height="16" />
    </content-loader>
</template>
<script>
    import { ContentLoader } from 'vue-content-loader'
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
                return this.$store.state.loadingConf
            }
        }
    }
</script>
