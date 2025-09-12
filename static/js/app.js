class RAGChatApp {
    constructor() {
        this.currentSessionId = this.generateSessionId();
        this.sessions = this.loadSessions();
        this.documents = [];
        this.isStreaming = false;
        this.currentStreamingMessage = null;
        
        this.initializeElements();
        this.setupEventListeners();
        this.checkHealth();
        this.loadDocuments();
        this.loadSessionsUI();
        
        // Configure marked for markdown rendering
        marked.setOptions({
            breaks: true,
            gfm: true,
            highlight: function(code, lang) {
                return code; // Simple highlighting, can be enhanced with Prism.js
            }
        });
    }
    
    initializeElements() {
        this.elements = {
            // Health status
            healthStatus: document.getElementById('healthStatus'),
            
            // File upload
            fileInput: document.getElementById('fileInput'),
            uploadStatus: document.getElementById('uploadStatus'),
            uploadProgress: document.getElementById('uploadProgress'),
            progressBar: document.getElementById('progressBar'),
            
            // Documents
            documentsList: document.getElementById('documentsList'),
            totalDocs: document.getElementById('totalDocs'),
            
            // Sessions
            sessionsList: document.getElementById('sessionsList'),
            activeSession: document.getElementById('activeSession'),
            newSessionBtn: document.getElementById('newSessionBtn'),
            
            // Chat
            chatContainer: document.getElementById('chatContainer'),
            messageInput: document.getElementById('messageInput'),
            sendBtn: document.getElementById('sendBtn'),
            sendIcon: document.getElementById('sendIcon'),
            sendSpinner: document.getElementById('sendSpinner'),
            streamingStatus: document.getElementById('streamingStatus'),
            
            // Controls
            clearChatBtn: document.getElementById('clearChatBtn'),
            clearCollectionBtn: document.getElementById('clearCollectionBtn')
        };
    }
    
    setupEventListeners() {
        // File upload
        this.elements.fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        
        // Chat input
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea
        this.elements.messageInput.addEventListener('input', () => {
            this.elements.messageInput.style.height = 'auto';
            this.elements.messageInput.style.height = Math.min(this.elements.messageInput.scrollHeight, 120) + 'px';
        });
        
        this.elements.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // Session management
        this.elements.newSessionBtn.addEventListener('click', () => this.createNewSession());
        
        // Clear buttons
        this.elements.clearChatBtn.addEventListener('click', () => this.clearChat());
        this.elements.clearCollectionBtn.addEventListener('click', () => this.clearCollection());
        
        // Periodic health check
        setInterval(() => this.checkHealth(), 30000);
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    async checkHealth() {
        try {
            const response = await fetch('/health');
            const data = await response.json();
            
            const statusElement = this.elements.healthStatus;
            if (data.status === 'healthy') {
                statusElement.innerHTML = `
                    <span class="inline-block w-2 h-2 bg-green-500 rounded-full mr-2 pulse-green"></span>
                    System healthy
                `;
            } else {
                statusElement.innerHTML = `
                    <span class="inline-block w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                    System error
                `;
            }
        } catch (error) {
            console.error('Health check failed:', error);
            this.elements.healthStatus.innerHTML = `
                <span class="inline-block w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                Connection error
            `;
        }
    }
    
    async loadDocuments() {
        try {
            const response = await fetch('/documents/stats');
            const stats = await response.json();
            this.elements.totalDocs.textContent = stats.total_documents || 0;
            
            // Load documents from localStorage for UI
            this.updateDocumentsUI();
            
        } catch (error) {
            console.error('Failed to load documents:', error);
            this.elements.totalDocs.textContent = 'Error';
        }
    }
    
    updateDocumentsUI() {
        const savedDocs = JSON.parse(localStorage.getItem('uploadedDocuments') || '[]');
        this.documents = savedDocs;
        
        if (this.documents.length === 0) {
            this.elements.documentsList.innerHTML = `
                <div class="text-center text-slate-500 py-4">
                    <svg class="mx-auto h-8 w-8 text-slate-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p class="text-sm">No documents uploaded</p>
                </div>
            `;
        } else {
            this.elements.documentsList.innerHTML = this.documents.map(doc => `
                <div class="bg-slate-700 rounded-lg p-3 border border-slate-600 hover:border-slate-500 transition-colors">
                    <div class="flex items-start justify-between">
                        <div class="flex-1 min-w-0">
                            <h3 class="text-sm font-medium text-white truncate" title="${doc.filename}">
                                📄 ${doc.filename}
                            </h3>
                            <p class="text-xs text-slate-400 mt-1">
                                ${doc.chunks_created} chunks • ${new Date(doc.uploaded_at).toLocaleDateString()}
                            </p>
                        </div>
                        <button onclick="ragApp.removeDocument('${doc.document_id}')" 
                                class="ml-2 text-red-400 hover:text-red-300 text-xs">
                            ✕
                        </button>
                    </div>
                </div>
            `).join('');
        }
    }
    
    removeDocument(documentId) {
        const savedDocs = JSON.parse(localStorage.getItem('uploadedDocuments') || '[]');
        const updatedDocs = savedDocs.filter(doc => doc.document_id !== documentId);
        localStorage.setItem('uploadedDocuments', JSON.stringify(updatedDocs));
        this.updateDocumentsUI();
    }
    
    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!file.type.includes('pdf')) {
            this.showUploadStatus('Please select a PDF file.', 'error');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        this.showUploadStatus('Uploading...', 'loading');
        this.elements.uploadProgress.classList.remove('hidden');
        
        try {
            const response = await fetch('/documents/upload', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showUploadStatus(`✅ ${result.message}`, 'success');
                
                // Save to localStorage for UI
                const docInfo = {
                    ...result,
                    uploaded_at: new Date().toISOString()
                };
                
                const savedDocs = JSON.parse(localStorage.getItem('uploadedDocuments') || '[]');
                savedDocs.push(docInfo);
                localStorage.setItem('uploadedDocuments', JSON.stringify(savedDocs));
                
                // Refresh UI
                this.loadDocuments();
                
                // Clear welcome message if it exists
                this.clearWelcomeMessage();
                
            } else {
                const error = await response.json();
                this.showUploadStatus(`❌ ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Upload failed:', error);
            this.showUploadStatus('❌ Upload failed', 'error');
        } finally {
            this.elements.uploadProgress.classList.add('hidden');
            this.elements.fileInput.value = '';
            
            setTimeout(() => {
                this.elements.uploadStatus.classList.add('hidden');
            }, 5000);
        }
    }
    
    showUploadStatus(message, type) {
        this.elements.uploadStatus.textContent = message;
        this.elements.uploadStatus.classList.remove('hidden', 'text-slate-400', 'text-green-400', 'text-red-400');
        
        switch(type) {
            case 'success':
                this.elements.uploadStatus.classList.add('text-green-400');
                break;
            case 'error':
                this.elements.uploadStatus.classList.add('text-red-400');
                break;
            default:
                this.elements.uploadStatus.classList.add('text-slate-400');
        }
    }
    
    clearWelcomeMessage() {
        const welcomeMsg = this.elements.chatContainer.querySelector('.text-center');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
    }
    
    async sendMessage() {
        const message = this.elements.messageInput.value.trim();
        if (!message || this.isStreaming) return;
        
        this.clearWelcomeMessage();
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input and reset height
        this.elements.messageInput.value = '';
        this.elements.messageInput.style.height = 'auto';
        
        // Set streaming state
        this.setStreamingState(true);
        
        try {
            // Create assistant message container
            const assistantMessage = this.addMessage('', 'assistant', true);
            this.currentStreamingMessage = assistantMessage.querySelector('.message-content');
            
            // Start streaming
            await this.streamChatResponse(message);
            
        } catch (error) {
            console.error('Chat error:', error);
            this.addMessage('Sorry, there was an error processing your message. Please try again.', 'assistant');
        } finally {
            this.setStreamingState(false);
            this.currentStreamingMessage = null;
        }
    }
    
    async streamChatResponse(message) {
        const response = await fetch('/documents/chat-stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: this.currentSessionId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedContent = '';
        
        try {
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        
                        if (data === '[DONE]') {
                            continue;
                        }
                        
                        try {
                            const parsed = JSON.parse(data);
                            
                            if (parsed.content) {
                                accumulatedContent += parsed.content;
                                this.updateStreamingMessage(accumulatedContent);
                            }
                            
                            if (parsed.sources && parsed.sources.length > 0) {
                                this.addSourcesToMessage(parsed.sources);
                            }
                            
                        } catch (e) {
                            console.warn('Failed to parse SSE data:', data);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Streaming error:', error);
        } finally {
            reader.releaseLock();
        }
    }
    
    updateStreamingMessage(content) {
        if (this.currentStreamingMessage) {
            // Remove typing indicator if present
            const typingIndicator = this.currentStreamingMessage.querySelector('.typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
            
            // Render markdown content
            const htmlContent = DOMPurify.sanitize(marked.parse(content));
            this.currentStreamingMessage.innerHTML = htmlContent;
            
            // Add typing indicator at the end
            const indicator = document.createElement('span');
            indicator.className = 'typing-indicator ml-1';
            this.currentStreamingMessage.appendChild(indicator);
            
            // Scroll to bottom
            this.scrollToBottom();
        }
    }
    
    addSourcesToMessage(sources) {
        if (this.currentStreamingMessage && sources.length > 0) {
            const messageDiv = this.currentStreamingMessage.closest('.fade-in');
            if (messageDiv) {
                // Remove existing sources if any
                const existingSources = messageDiv.querySelector('.sources');
                if (existingSources) {
                    existingSources.remove();
                }
                
                // Add new sources
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'sources mt-3 text-xs text-slate-400 border-t border-slate-700 pt-2';
                sourcesDiv.innerHTML = `
                    <div class="font-medium mb-1">Sources:</div>
                    ${sources.map(source => `<div class="mb-1">📄 ${source}</div>`).join('')}
                `;
                messageDiv.appendChild(sourcesDiv);
            }
        }
    }
    
    setStreamingState(streaming) {
        this.isStreaming = streaming;
        
        if (streaming) {
            this.elements.sendBtn.disabled = true;
            this.elements.sendIcon.classList.add('hidden');
            this.elements.sendSpinner.classList.remove('hidden');
            this.elements.streamingStatus.classList.remove('hidden');
        } else {
            this.elements.sendBtn.disabled = false;
            this.elements.sendIcon.classList.remove('hidden');
            this.elements.sendSpinner.classList.add('hidden');
            this.elements.streamingStatus.classList.add('hidden');
            
            // Remove typing indicator from final message
            if (this.currentStreamingMessage) {
                const typingIndicator = this.currentStreamingMessage.querySelector('.typing-indicator');
                if (typingIndicator) {
                    typingIndicator.remove();
                }
            }
        }
    }
    
    addMessage(content, sender, isStreaming = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'fade-in';
        
        const isUser = sender === 'user';
        const alignClass = isUser ? 'justify-end' : 'justify-start';
        const bgClass = isUser ? 'bg-blue-600' : 'bg-slate-700';
        const textClass = isUser ? 'text-white' : 'text-slate-100';
        
        messageDiv.innerHTML = `
            <div class="flex ${alignClass} mb-4">
                <div class="max-w-3xl ${bgClass} ${textClass} rounded-2xl px-4 py-3 shadow-lg">
                    ${isUser ? '' : '<div class="flex items-center mb-2"><svg class="w-4 h-4 mr-2 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>Assistant</div>'}
                    <div class="message-content ${isUser ? '' : 'markdown-content'}">
                        ${isUser ? content : (isStreaming ? '<span class="typing-indicator"></span>' : DOMPurify.sanitize(marked.parse(content)))}
                    </div>
                </div>
            </div>
        `;
        
        this.elements.chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Save to session
        this.saveMessageToSession({
            content,
            sender,
            timestamp: new Date().toISOString()
        });
        
        return messageDiv;
    }
    
    scrollToBottom() {
        this.elements.chatContainer.scrollTop = this.elements.chatContainer.scrollHeight;
    }
    
    // Session Management
    loadSessions() {
        return JSON.parse(localStorage.getItem('chatSessions') || '{}');
    }
    
    saveSessions() {
        localStorage.setItem('chatSessions', JSON.stringify(this.sessions));
    }
    
    saveMessageToSession(message) {
        if (!this.sessions[this.currentSessionId]) {
            this.sessions[this.currentSessionId] = {
                id: this.currentSessionId,
                title: message.content.slice(0, 50) + (message.content.length > 50 ? '...' : ''),
                messages: [],
                createdAt: new Date().toISOString()
            };
        }
        
        this.sessions[this.currentSessionId].messages.push(message);
        this.saveSessions();
        this.loadSessionsUI();
    }
    
    loadSessionsUI() {
        const sessionsList = this.elements.sessionsList;
        const sessions = Object.values(this.sessions).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        
        if (sessions.length === 0) {
            sessionsList.innerHTML = `
                <div class="text-center text-slate-500 py-2">
                    <p class="text-sm">No chat sessions yet</p>
                </div>
            `;
        } else {
            sessionsList.innerHTML = sessions.map(session => `
                <div class="flex items-center justify-between p-2 rounded hover:bg-slate-700 cursor-pointer ${session.id === this.currentSessionId ? 'bg-slate-600' : ''}"
                     onclick="ragApp.loadSession('${session.id}')">
                    <div class="flex-1 min-w-0">
                        <div class="text-sm text-white truncate">${session.title}</div>
                        <div class="text-xs text-slate-400">${new Date(session.createdAt).toLocaleDateString()}</div>
                    </div>
                    <button onclick="event.stopPropagation(); ragApp.deleteSession('${session.id}')" 
                            class="text-red-400 hover:text-red-300 text-xs ml-2">
                        ✕
                    </button>
                </div>
            `).join('');
        }
        
        // Update active session display
        this.elements.activeSession.textContent = this.currentSessionId.slice(-8);
    }
    
    createNewSession() {
        this.currentSessionId = this.generateSessionId();
        this.clearChat();
        this.loadSessionsUI();
    }
    
    loadSession(sessionId) {
        this.currentSessionId = sessionId;
        const session = this.sessions[sessionId];
        
        if (session) {
            // Clear current chat
            this.elements.chatContainer.innerHTML = '';
            
            // Load session messages
            session.messages.forEach(msg => {
                this.addMessage(msg.content, msg.sender);
            });
        }
        
        this.loadSessionsUI();
    }
    
    deleteSession(sessionId) {
        delete this.sessions[sessionId];
        this.saveSessions();
        
        if (sessionId === this.currentSessionId) {
            this.createNewSession();
        } else {
            this.loadSessionsUI();
        }
    }
    
    clearChat() {
        this.elements.chatContainer.innerHTML = `
            <div class="text-center text-slate-400 mt-8">
                <svg class="w-16 h-16 mx-auto mb-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-3.582 8-8 8a8.955 8.955 0 01-4.906-1.471L3 21l1.471-5.094A8.955 8.955 0 013 12c0-4.418 3.582-8 8-8s8 3.582 8 8z"></path>
                </svg>
                <p class="text-lg font-medium">Welcome to RAG Pipeline Chat</p>
                <p class="text-sm mt-2">Upload a PDF document and start asking questions!</p>
            </div>
        `;
    }
    
    async clearCollection() {
        if (confirm('Are you sure you want to clear all documents? This cannot be undone.')) {
            try {
                const response = await fetch('/documents/clear', { method: 'DELETE' });
                if (response.ok) {
                    // Clear localStorage
                    localStorage.removeItem('uploadedDocuments');
                    
                    // Refresh UI
                    this.updateDocumentsUI();
                    this.loadDocuments();
                    
                    // Reset collection
                    await fetch('/documents/reset', { method: 'POST' });
                    
                    alert('Collection cleared successfully!');
                } else {
                    throw new Error('Failed to clear collection');
                }
            } catch (error) {
                console.error('Clear collection error:', error);
                alert('Failed to clear collection. Please try again.');
            }
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.ragApp = new RAGChatApp();
});