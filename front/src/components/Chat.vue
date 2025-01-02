<template>
    <div class="chat-container">
        <div class="messages" ref="messagesContainer">
            <div v-for="(message, index) in messages" 
                :key="index" 
                :class="['message', message.role]"
            >
                <div class="message-content">
                    {{ message.content }}
                    <span v-if="isStreaming && index === messages.length - 1" class="cursor"></span>
                </div>
            </div>
        </div>
        
        <div class="input-container">
            <div class="input-wrapper">
                <textarea
                    v-model="userInput"
                    @keydown.enter.prevent="sendMessage"
                    placeholder="Send a message..."
                    rows="1"
                    ref="textareaRef"
                    :disabled="isStreaming"
                ></textarea>
                <button 
                    @click="sendMessage" 
                    class="send-button"
                    :disabled="isStreaming"
                >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <path d="M7 11L12 6L17 11M12 18V7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

interface Message {
    role: 'user' | 'assistant' | 'system'
    content: string
}

const props = defineProps<{
    threadId?: string
}>()

const messages = ref<Message[]>([])
const userInput = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const isStreaming = ref(false)

const fetchThreadData = async (id: string) => {
    try {
        const response = await fetch(`/api/chat/thread/${id}/`)
        const data = await response.json()
        messages.value = data.messages || []
    } catch (error) {
        console.error('Failed to fetch thread data:', error)
    }
}

watch(() => props.threadId, (newId) => {
    if (newId) {
        fetchThreadData(newId)
    }
})

onMounted(() => {
    if (props.threadId) {
        fetchThreadData(props.threadId)
    }
})

const sendMessage = async () => {
    if (!userInput.value.trim() || !props.threadId || isStreaming.value) return

    const messageContent = userInput.value
    userInput.value = ''

    // Add user message
    messages.value.push({
        role: 'user',
        content: messageContent
    })

    // Add initial assistant message that will be updated with the stream
    messages.value.push({
        role: 'assistant',
        content: ''
    })

    try {
        isStreaming.value = true
        const response = await fetch(`/api/chat/thread/${props.threadId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ content: messageContent })
        })

        const reader = response.body?.getReader()
        if (!reader) throw new Error('No reader available')

        // Get the last message (assistant's message) to update
        const assistantMessage = messages.value[messages.value.length - 1]
        
        while (true) {
            const { done, value } = await reader.read()
            if (done) break

            // Convert the chunk to text
            const chunk = new TextDecoder().decode(value)
            // Append the new chunk to the assistant's message
            assistantMessage.content += chunk

            // Scroll to bottom
            if (messagesContainer.value) {
                messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
            }
        }
    } catch (error) {
        console.error('Failed to send message:', error)
        messages.value.push({
            role: 'system',
            content: 'Failed to send message. Please try again.'
        })
    } finally {
        isStreaming.value = false
    }
}

// Auto-scroll when new messages arrive
watch(() => messages.value.length, () => {
    if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
})
</script>

<style scoped>
.chat-container {
    height: 100%;
    display: flex;
    flex-direction: column;
}

.messages {
    flex-grow: 1;
    overflow-y: auto;
    padding: 2rem;
}

.message {
    display: flex;
    padding: 1.5rem;
    margin-bottom: 1rem;
}

.message.user {
    background-color: #343541;
}

.message.assistant {
    background-color: #444654;
}

.message-content {
    max-width: 768px;
    margin: 0 auto;
    color: #ececf1;
    line-height: 1.6;
}

.input-container {
    padding: 2rem;
    background-color: #343541;
    border-top: 1px solid #4d4d4f;
}

.input-wrapper {
    max-width: 768px;
    margin: 0 auto;
    position: relative;
}

textarea {
    width: 100%;
    background-color: #40414f;
    border: 1px solid #565869;
    border-radius: 0.5rem;
    color: white;
    font-size: 1rem;
    padding: 0.75rem 2.5rem 0.75rem 0.75rem;
    resize: none;
    outline: none;
}

.send-button {
    position: absolute;
    right: 0.5rem;
    bottom: 0.5rem;
    background: none;
    border: none;
    color: #ececf1;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 0.25rem;
}

.send-button:hover {
    background-color: #565869;
}

.cursor {
    display: inline-block;
    width: 0.5em;
    height: 1em;
    background-color: #ececf1;
    margin-left: 2px;
    animation: blink 1s infinite;
}

@keyframes blink {
    0% { opacity: 1; }
    50% { opacity: 0; }
    100% { opacity: 1; }
}

textarea:disabled,
button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
</style>