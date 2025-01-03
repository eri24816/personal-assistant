<template>
    <div class="app-container">
        <div class="left-column">
            <div class="thread-list">
                <div class="thread-item new-thread" @click="createNewThread">
                    <span>New Chat</span>
                </div>
                <div
                    v-for="thread in threads"
                    :key="thread.id"
                    :class="['thread-item', { active: selectedThread?.id === thread.id }]"
                >
                    <div class="thread-item-content" @click="selectThread(thread)">
                        {{ thread.title }}
                    </div>
                    <button 
                        class="delete-button"
                        @click="deleteThread(thread)"
                        :title="'Delete ' + thread.title"
                    >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2M10 11v6M14 11v6" 
                                stroke-width="2" 
                                stroke-linecap="round" 
                                stroke-linejoin="round"
                            />
                        </svg>
                    </button>
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
        const data = await response.json()
        threads.value = Object.values(data)
        threads.value.reverse()
        if (threads.value.length > 0 && !selectedThread.value) {
            selectedThread.value = threads.value[0]
        }
    } catch (error) {
        console.error('Failed to fetch threads:', error)
    }
}

const selectThread = (thread: Thread) => {
    selectedThread.value = thread
}

const createNewThread = async () => {
    try {
        const response = await fetch('/api/chat/threads/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        })
        const newThread = await response.json()
        threads.value.unshift(newThread)
        selectedThread.value = newThread
    } catch (error) {
        console.error('Failed to create thread:', error)
    }
}

const deleteThread = async (thread: Thread) => {
    if (!confirm(`Are you sure you want to delete "${thread.title}"?`)) {
        return
    }

    try {
        await fetch(`/api/chat/thread/${thread.id}`, {
            method: 'DELETE',
        })
        console.log('deleted thread', thread)
        const index = threads.value.findIndex(t => t.id === thread.id)
        if (index !== -1) {
            threads.value.splice(index, 1)
        }

        if (selectedThread.value?.id === thread.id) {
            selectedThread.value = threads.value[0] || null
        }
    } catch (error) {
        console.error('Failed to delete thread:', error)
    }
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
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0;
    border-radius: 6px;
    color: #fff;
    transition: background-color 0.2s;
}

.thread-item-content {
    flex-grow: 1;
    padding: 12px;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.new-thread {
    padding: 12px;
    cursor: pointer;
    border: 1px dashed #4d4d4f;
    justify-content: center;
    margin-bottom: 8px;
}

.new-thread:hover {
    background-color: #2a2b32;
    border-color: #565869;
}

.thread-item:hover {
    background-color: #2a2b32;
}

.thread-item.active {
    background-color: #343541;
}

.delete-button {
    visibility: hidden;
    background: none;
    border: none;
    color: #666;
    cursor: pointer;
    padding: 8px;
    opacity: 0.8;
    transition: all 0.2s;
    border-radius: 4px;
}

.thread-item:hover .delete-button {
    visibility: visible;
}

.delete-button:hover {
    color: #ff4444;
    opacity: 1;
    background-color: rgba(255, 68, 68, 0.1);
}
</style>