<template>
    <div class="content-renderer">
        <template v-if="looksLikeJson && parsedContent">
            <div v-if="Array.isArray(parsedContent)" class="json-array">
                <div v-for="(item, index) in parsedContent" :key="index" class="json-item">
                    <ContentRenderer :content="item" />
                </div>
            </div>
            <div v-else-if="typeof parsedContent === 'object'" class="json-object">
                <div v-for="(value, key) in parsedContent" 
                    :key="key" 
                    class="json-field"
                >
                    <div class="json-key">{{ formatKey(key) }}:</div>
                    <div class="json-value">
                        <ContentRenderer :content="value" />
                    </div>
                </div>
            </div>
            <!-- handle numbers -->
            <div v-else-if="typeof parsedContent === 'number'" class="json-number">
                {{ parsedContent }}
            </div>
        </template>
        <template v-else>
            {{ content }}
            <span v-if="isStreaming" class="cursor"></span>
        </template>
    </div>
</template>

<script setup lang="ts">
import { IncompleteJsonParser } from 'incomplete-json-parser';
import { computed } from 'vue'

const props = defineProps<{
    content: any
    isStreaming?: boolean
}>()

const looksLikeJson = computed(() => {
    if (typeof props.content === 'object') return true
    if (typeof props.content !== 'string') return false
    if (!props.isStreaming){
        try {
            JSON.parse(props.content)
            return true
        } catch {
            return false
        }
    }
    const trimmed = props.content.replace(/^[ \t\n\r]+/, '')
    console.log(trimmed)
    if (/^\{\"/.test(trimmed) ||
        /^\{\[0-9]/.test(trimmed) ||
        /^\{\{/.test(trimmed) ||
        /^\{\[/.test(trimmed)
    ) {
        return true
    }
    if (
        /^\[\]/.test(trimmed) 
        || /^\[\[0-9]/.test(trimmed) 
        || /^\[\{/.test(trimmed) 
        || /^\[\"/.test(trimmed) ) {
        return true
    }
    return false
})

const parsedContent = computed(() => {
    if (!looksLikeJson.value) return null
    if (typeof props.content === 'object') return props.content

    if (!props.isStreaming && typeof props.content === 'string') return JSON.parse(props.content)
    try {
        return IncompleteJsonParser.parse(props.content)
    } catch {
        return null
    }
})

const formatKey = (key: string | number) => {
    const keyStr = String(key)
    return keyStr
        .replace(/([A-Z])/g, ' $1')
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ')
}
</script>

<style scoped>
.content-renderer {
    width: 100%;
}

.json-object {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.json-field {
    display: flex;
    gap: 0.5rem;
    align-items: flex-start;
}

.json-key {
    color: #89CFF0;  /* Light blue color for keys */
    min-width: 120px;
    font-weight: 500;
}

.json-value {
    flex: 1;
}

.json-array {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.json-item {
    padding-left: 1rem;
    border-left: 2px solid #4d4d4f;
}

.cursor {
    display: inline-block;
    width: 0.5em;
    height: 1em;
    background-color: #ececf1;
    margin-left: 2px;
    animation: blink 1s infinite;
}

.json-number {
    color: #7dd888;  /* Light green color for numbers */
    min-width: 120px;
    font-weight: 500;
}

@keyframes blink {
    0% { opacity: 1; }
    50% { opacity: 0; }
    100% { opacity: 1; }
}
</style> 