<template>
    <deploy-action
        :environment="'prod'">
    </deploy-action>
</template>

<script>
    import deployAction from './comps/deploy-action';

    export default {
        components: {
            deployAction
        },
        props: {
            moduleId: {
                type: String,
                default: ''
            }
        }
    };
</script>
