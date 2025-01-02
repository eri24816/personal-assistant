<template>
    <div class="app-container">
        <div class="left-column">
            <div class="thread-list">
                <div class="thread-item" @click="createNewThread">
                    New Chat
                </div>
                <div
                    v-for="thread in threads"
                    :key="thread.id"
                    :class="['thread-item', { active: selectedThread?.id === thread.id }]"
                    @click="selectThread(thread)"
                >
                    {{ thread.title }}
                </div>
            </div>
        </div>
        <div class="main-column">
            <Chat :thread-id="selectedThread?.id" />
        </div>
        <div class="right-column">
            <!-- Right sidebar content will go here -->
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Chat from './components/Chat.vue'

interface Thread {
    id: string
    title: string
}

const threads = ref<Thread[]>([])
const selectedThread = ref<Thread | null>(null)

const fetchThreads = async () => {
    try {
        const response = await fetch('/api/chat/threads/')
        threads.value = await response.json()
        if (threads.value.length > 0) {
            selectedThread.value = threads.value[0]
        }
    } catch (error) {
        console.error('Failed to fetch threads:', error)
    }
}

const selectThread = (thread: Thread) => {
    selectedThread.value = thread
}

// TODO: create new thread call post /api/chat/threads/
const createNewThread = async () => {
    const response = await fetch('/api/chat/threads/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
}

onMounted(() => {
    fetchThreads()
})
</script>

<style scoped>
.app-container {
    display: grid;
    grid-template-columns: 260px 1fr 260px;
    height: 100vh;
    width: 100%;
}

.left-column {
    background-color: #202123;
    border-right: 1px solid #4d4d4f;
    padding: 8px;
}

.main-column {
    background-color: #343541;
    overflow-y: auto;
}

.right-column {
    background-color: #202123;
    border-left: 1px solid #4d4d4f;
}

.thread-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.thread-item {
    padding: 12px;
    border-radius: 6px;
    cursor: pointer;
    color: #fff;
    transition: background-color 0.2s;
}

.thread-item:hover {
    background-color: #2a2b32;
}

.thread-item.active {
    background-color: #343541;
}
</style>