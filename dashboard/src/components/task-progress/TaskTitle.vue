<script setup lang="ts">
defineProps<{ text: string }>();
</script>
<template><span class="full-task-title" :title="text">{{ text }}</span></template>
<style scoped>
.full-task-title { display:block; min-width:0; max-width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:11px; line-height:16px; }
</style>
