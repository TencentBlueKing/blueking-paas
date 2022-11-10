<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="636"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="1" y="0" rx="2" ry="2" :width="baseWidth" height="46" />
        <rect x="1" y="62" rx="1" ry="1" width="100" height="20" />
        <rect x="1" y="86" rx="1" ry="1" width="310" height="16" />
        <rect x="1" y="140" rx="1" ry="1" :width="baseWidth" height="250" />
        <rect x="1" y="430" rx="1" ry="1" width="100" height="20" />
        <rect x="1" y="454" rx="1" ry="1" width="414" height="16" />
        <rect x="1" y="500" rx="1" ry="1" width="100" height="20" />
        <rect x="120" y="500" rx="1" ry="1" width="100" height="20" />
        <rect x="1" y="530" rx="1" ry="1" :width="baseWidth" height="50" />

        <!-- <rect x="0" y="58" rx="2" ry="2" :width="baseWidth" height="42" />
        <rect x="0" y="113" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="154" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="195" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="236" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="277" rx="1" ry="1" :width="baseWidth" height="20" />
        <rect x="0" y="318" rx="1" ry="1" :width="baseWidth" height="20" />  -->
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
