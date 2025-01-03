<template>
    <div class="chat-container">
        <div class="messages" ref="messagesContainer">
            <div v-for="(message, index) in uiMessages" 
                :key="index" 
                :class="['message', message.role]"
            >
                <div class="message-header" v-if="message.header">
                    {{ message.header }}
                </div>
                <ContentRenderer 
                    class="message-content" 
                    :content="message.content" 
                    :isStreaming="isStreaming && index === uiMessages.length - 1" 
                />
                <div v-if="message.collapsableContent" class="collapsable-container">
                    <button 
                        class="collapse-toggle"
                        @click="toggleCollapse(index)"
                        :aria-expanded="!collapsedStates[index]"
                    >
                        {{ collapsedStates[index] ? 'Show details' : 'Hide details' }}
                        <svg 
                            class="chevron"
                            :class="{ 'chevron-down': collapsedStates[index] }"
                            width="16" 
                            height="16" 
                            viewBox="0 0 16 16"
                        >
                            <path d="M3.5 5.5l4.5 4.5 4.5-4.5" fill="none" stroke="currentColor" stroke-width="1.5"/>
                        </svg>
                    </button>
                    <div 
                        class="message-collapsable-content"
                        :class="{ collapsed: collapsedStates[index] }"
                    >
                        <ContentRenderer 
                            :content="message.collapsableContent" 
                            :isStreaming="isStreaming && index === uiMessages.length - 1" 
                        />
                    </div>
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
import ContentRenderer from './ContentRenderer.vue'
import { IncompleteJsonParser } from 'incomplete-json-parser'
import { ref, onMounted, watch } from 'vue'

interface Message {
    role: 'user' | 'ai' | 'system'
    content: string
    header?: string
    collapsableContent?: string
}

const props = defineProps<{
    threadId?: string
}>()

const uiMessages = ref<Message[]>([])
const userInput = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const isStreaming = ref(false)
const collapsedStates = ref<Record<number, boolean>>({})

const fetchThreadData = async (id: string) => {

    const response = await fetch(`/api/chat/thread/${id}/`)
    const payload = await response.json()
    uiMessages.value = []
    if (payload.state == null) {
        return // empty thread
    }
    const rawMessages = payload.state.messages
    const toolCallMessages = new Map<string, Message>() // id -> message
    for (const message of rawMessages) {
        processMessage(message, toolCallMessages)
    } 
}

const processMessage = (message: any, toolCallMessages: Map<string, Message>) => {
    if (message.type == 'ai') {
        if (message.content != '') {
            uiMessages.value.push({
                role: 'ai',
                content: message.content
            })
        }

        for (const toolCall of message.tool_calls) {
            toolCallMessages.set(toolCall.id, {
                role: 'system',
                header: toolCall.name,
                content: toolCall.args
            })
            uiMessages.value.push(toolCallMessages.get(toolCall.id)!)
        }
        
    }
    else if (message.type == 'human') {
        uiMessages.value.push({
            role: 'user',
            content: message.content
        })
    }else if (message.type == 'tool') {
        let uiMessage: Message | undefined = toolCallMessages.get(message.tool_call_id)
        if (uiMessage == undefined) {
            uiMessage = {
                role: 'system',
                content: 'missing'
            }
            uiMessages.value.push(uiMessage)
        }
        uiMessage.collapsableContent = message.content
        if (message.artifact != null) {
            uiMessage.collapsableContent += message.artifact[0].page_content
        }
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
    uiMessages.value.push({
        role: 'user',
        content: messageContent
    })

    try {
        isStreaming.value = true
        let accumulatingMessage: Message = {
            role: 'ai',
            content: ''
        }
        uiMessages.value.push(accumulatingMessage)
        scrollToBottom()
        const response = await fetch(`/api/chat/thread/${props.threadId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ content: messageContent })
        })

        const reader = response.body?.getReader()
        if (!reader) throw new Error('No reader available')

        while (true) {
            const { done, value } = await reader.read()
            if (done) break
            
            const payloadString = new TextDecoder().decode(value)
            //sometimes the value have multiple lines, so we need to split it
            // Convert the chunk to text
            for (const line of payloadString.split('\n')) { 
                (window as any).debug = line
                if (line.trim() == '') continue
                const payload = JSON.parse(line)
                // Append the new chunk to the assistant's message
                const chunk = payload.chunk
                accumulatingMessage = processMessageChunk(chunk, accumulatingMessage) || accumulatingMessage
            }
        }
    } catch (error) {
        console.error('Error processing message:', error)
        uiMessages.value.push({
            role: 'system',
            content: 'Failed to send message. Please try again.'
        })
    } finally {
        isStreaming.value = false
    }
}


const processMessageChunk = (chunk: any, accumulatingMessage: Message) => {
    let currentRole: 'user' | 'ai' | 'system' = 'ai'
    if (chunk.type === 'AIMessageChunk') {
        if (chunk.content == '') {
            return
        }
        currentRole = 'ai'
    } else if (chunk.type === 'tool_call_chunk' || chunk.type === 'tool') {
        currentRole = 'system'
    }else{
        throw new Error('Unknown chunk type: ' + chunk.type)
    }
    
    if(accumulatingMessage.role !== currentRole) {
        if (accumulatingMessage.content == ''){
            const poppedMessage = uiMessages.value.pop()
        }
        // collapse the previous message
        const lastMessageId = uiMessages.value.length - 1
        collapsedStates.value[lastMessageId] = true
        accumulatingMessage = { role: currentRole, content: '' }
        uiMessages.value.push(accumulatingMessage)
    }
    
    // Append the new chunk to the assistant's message
    if (chunk.type === 'AIMessageChunk') {
        accumulatingMessage.content += chunk.content
    }else if (chunk.type === 'tool_call_chunk') {
        accumulatingMessage.content += chunk.args
        if (chunk.name !== null) {
            accumulatingMessage.header = chunk.name
        }
    }else if (chunk.type === 'tool') {
        accumulatingMessage.collapsableContent = chunk.content
    }
    
    // doing this so vue can detect the change
    const lastMessage = uiMessages.value.pop()!
    uiMessages.value.push(lastMessage)
    
    scrollToBottom()

    return accumulatingMessage
}

const scrollToBottom = () => {
    setTimeout(() => {
        if (messagesContainer.value) {
            messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
    }, 300)
}

// Auto-scroll when new messages arrive
watch(() => uiMessages, () => {
    if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
}, { deep: true })

const toggleCollapse = (index: number) => {
    collapsedStates.value[index] = !collapsedStates.value[index]
}

// Initialize collapse state for new messages
watch(() => uiMessages, () => {
    const lastIndex = uiMessages.value.length - 1
    if (uiMessages.value[lastIndex]?.collapsableContent) {
        collapsedStates.value[lastIndex] = false
    }
}, { deep: true })
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
    flex-direction: column;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid #4d4d4f;
}

.message.user {
    background-color: #343541;
}

.message.ai {
    background-color: #444654;
}

.message.system {
    background-color: #2a2b32;
    font-family: monospace;
}

.message-header {
    color: #ececf1;
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
    font-weight: 500;
    opacity: 0.8;
    text-transform: uppercase;
}

.message-content {
    max-width: 768px;
    margin: 0 auto;
    color: #ececf1;
    line-height: 1.6;
    width: 100%;
    white-space: pre-wrap;
    word-wrap: break-word;
}

.collapsable-container {
    margin-top: 0.5rem;
}

.collapse-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: none;
    border: none;
    color: #ececf1;
    cursor: pointer;
    padding: 0.5rem;
    font-size: 0.9rem;
    opacity: 0.8;
    transition: opacity 0.2s;
}

.collapse-toggle:hover {
    opacity: 1;
}

.chevron {
    transition: transform 0.2s ease;
}

.chevron-down {
    transform: rotate(180deg);
}

.message-collapsable-content {
    color: #ececf1;
    line-height: 1.6;
    background-color: #2a2b32;
    padding: 1rem;
    margin-top: 0.5rem;
    border-radius: 0.5rem;
    font-family: monospace;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 0.9rem;
    border: 1px solid #4d4d4f;
    transition: max-height 0.3s ease-out, opacity 0.3s ease-out;
    max-height: 500px;
    opacity: 1;
    overflow: hidden;
}

.message-collapsable-content.collapsed {
    max-height: 0;
    opacity: 0;
    padding: 0;
    margin: 0;
    border: none;
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