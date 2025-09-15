class RAGChatApp {
    constructor() {
        // RAG properties
        this.currentSessionId = this.generateSessionId();
        this.sessions = this.loadSessions();
        this.documents = [];
        this.isStreaming = false;
        this.currentStreamingMessage = null;
        
        // Analytics properties
        this.activeMode = 'rag'; // 'rag' or 'analytics'
        this.databaseConnection = null;
        this.isAnalyzing = false;
        this.tables = [];
        
        this.initializeElements();
        this.setupEventListeners();
        this.toggleDatabaseFields(); // Initialize database form fields
        this.updateStrategyDescription(); // Initialize strategy description
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
            
            // Mode tabs
            ragTab: document.getElementById('ragTab'),
            analyticsTab: document.getElementById('analyticsTab'),
            
            // Content sections
            ragContent: document.getElementById('ragContent'),
            analyticsContent: document.getElementById('analyticsContent'),
            ragSidebar: document.getElementById('ragSidebar'),
            analyticsSidebar: document.getElementById('analyticsSidebar'),
            
            // Header elements
            mainTitle: document.getElementById('mainTitle'),
            mainSubtitle: document.getElementById('mainSubtitle'),
            ragControls: document.getElementById('ragControls'),
            analyticsControls: document.getElementById('analyticsControls'),
            
            // Display containers
            chatContainer: document.getElementById('chatContainer'),
            analyticsContainer: document.getElementById('analyticsContainer'),
            analyticsFrame: document.getElementById('analyticsFrame'),
            
            // Input elements
            messageInput: document.getElementById('messageInput'),
            sendBtn: document.getElementById('sendBtn'),
            sendText: document.getElementById('sendText'),
            sendIcon: document.getElementById('sendIcon'),
            sendSpinner: document.getElementById('sendSpinner'),
            inputHint: document.getElementById('inputHint'),
            streamingStatus: document.getElementById('streamingStatus'),
            streamingText: document.getElementById('streamingText'),
            
            // RAG elements
            fileInput: document.getElementById('fileInput'),
            uploadStatus: document.getElementById('uploadStatus'),
            uploadProgress: document.getElementById('uploadProgress'),
            progressBar: document.getElementById('progressBar'),
            documentsList: document.getElementById('documentsList'),
            totalDocs: document.getElementById('totalDocs'),
            sessionsList: document.getElementById('sessionsList'),
            activeSession: document.getElementById('activeSession'),
            newSessionBtn: document.getElementById('newSessionBtn'),
            clearChatBtn: document.getElementById('clearChatBtn'),
            clearCollectionBtn: document.getElementById('clearCollectionBtn'),
            ragStats: document.getElementById('ragStats'),
            
            // Analytics elements
            dbType: document.getElementById('dbType'),
            dbPath: document.getElementById('dbPath'),
            sqliteSection: document.getElementById('sqliteSection'),
            postgresqlSection: document.getElementById('postgresqlSection'),
            pgHost: document.getElementById('pgHost'),
            pgPort: document.getElementById('pgPort'),
            pgDatabase: document.getElementById('pgDatabase'),
            pgUsername: document.getElementById('pgUsername'),
            pgSchema: document.getElementById('pgSchema'),
            pgPassword: document.getElementById('pgPassword'),
            testConnectionBtn: document.getElementById('testConnectionBtn'),
            connectionStatus: document.getElementById('connectionStatus'),
            tablesList: document.getElementById('tablesList'),
            clearAnalyticsBtn: document.getElementById('clearAnalyticsBtn'),
            openAnalyticsBtn: document.getElementById('openAnalyticsBtn'),
            analyticsStats: document.getElementById('analyticsStats'),
            dbStatus: document.getElementById('dbStatus'),
            tablesCount: document.getElementById('tablesCount'),
            lastQueryTime: document.getElementById('lastQueryTime')
        };
    }
    
    setupEventListeners() {
        // Mode switching
        this.elements.ragTab.addEventListener('click', () => this.switchMode('rag'));
        this.elements.analyticsTab.addEventListener('click', () => this.switchMode('analytics'));
        
        // File upload
        this.elements.fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        
        // Input handling
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
        
        // RAG controls
        this.elements.newSessionBtn.addEventListener('click', () => this.createNewSession());
        this.elements.clearChatBtn.addEventListener('click', () => this.clearChat());
        this.elements.clearCollectionBtn.addEventListener('click', () => this.clearCollection());
        
        // Analytics controls
        this.elements.dbType.addEventListener('change', () => this.toggleDatabaseFields());
        this.elements.testConnectionBtn.addEventListener('click', () => this.testDatabaseConnection());
        this.elements.clearAnalyticsBtn.addEventListener('click', () => this.clearAnalytics());
        this.elements.openAnalyticsBtn.addEventListener('click', () => this.openAnalyticsInNewWindow());
        
        // Query strategy selector
        const queryStrategy = document.getElementById('queryStrategy');
        if (queryStrategy) {
            queryStrategy.addEventListener('change', () => this.updateStrategyDescription());
        }
        
        // Periodic health check
        setInterval(() => this.checkHealth(), 30000);
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    // Mode Management
    switchMode(mode) {
        this.activeMode = mode;
        
        // Update tab styling
        if (mode === 'rag') {
            this.elements.ragTab.className = 'flex-1 py-2 px-3 text-sm font-medium rounded-md transition-colors duration-200 bg-blue-600 text-white';
            this.elements.analyticsTab.className = 'flex-1 py-2 px-3 text-sm font-medium rounded-md transition-colors duration-200 text-slate-300 hover:text-white hover:bg-slate-600';
            
            // Show/hide content
            this.elements.ragContent.classList.remove('hidden');
            this.elements.analyticsContent.classList.add('hidden');
            this.elements.ragSidebar.classList.remove('hidden');
            this.elements.analyticsSidebar.classList.add('hidden');
            this.elements.chatContainer.classList.remove('hidden');
            this.elements.analyticsContainer.classList.add('hidden');
            this.elements.ragControls.classList.remove('hidden');
            this.elements.analyticsControls.classList.add('hidden');
            this.elements.ragStats.classList.remove('hidden');
            this.elements.analyticsStats.classList.add('hidden');
            
            // Update header
            this.elements.mainTitle.textContent = 'Chat Interface';
            this.elements.mainSubtitle.textContent = 'Ask questions about your uploaded documents';
            this.elements.inputHint.textContent = 'Press Shift+Enter for new line, Enter to send';
            this.elements.sendText.textContent = 'Send';
            this.elements.messageInput.placeholder = 'Type your question here...';
            
        } else if (mode === 'analytics') {
            this.elements.analyticsTab.className = 'flex-1 py-2 px-3 text-sm font-medium rounded-md transition-colors duration-200 bg-blue-600 text-white';
            this.elements.ragTab.className = 'flex-1 py-2 px-3 text-sm font-medium rounded-md transition-colors duration-200 text-slate-300 hover:text-white hover:bg-slate-600';
            
            // Show/hide content
            this.elements.ragContent.classList.add('hidden');
            this.elements.analyticsContent.classList.remove('hidden');
            this.elements.ragSidebar.classList.add('hidden');
            this.elements.analyticsSidebar.classList.remove('hidden');
            this.elements.chatContainer.classList.add('hidden');
            this.elements.analyticsContainer.classList.remove('hidden');
            this.elements.ragControls.classList.add('hidden');
            this.elements.analyticsControls.classList.remove('hidden');
            this.elements.ragStats.classList.add('hidden');
            this.elements.analyticsStats.classList.remove('hidden');
            
            // Update header
            this.elements.mainTitle.textContent = 'Database Analytics';
            this.elements.mainSubtitle.textContent = 'Connect to a database and generate analytics from natural language queries';
            this.updateAnalyticsInputHint();
            this.elements.sendText.textContent = 'Analyze';
            this.elements.messageInput.placeholder = 'Describe what you want to analyze...';
        }
    }
    
    // Analytics Methods
    toggleDatabaseFields() {
        const dbType = this.elements.dbType.value;
        
        if (dbType === 'sqlite') {
            this.elements.sqliteSection.classList.remove('hidden');
            this.elements.postgresqlSection.classList.add('hidden');
        } else if (dbType === 'postgresql') {
            this.elements.sqliteSection.classList.add('hidden');
            this.elements.postgresqlSection.classList.remove('hidden');
        }
        
        // Clear connection status when switching
        this.elements.connectionStatus.classList.add('hidden');
        this.databaseConnection = null;
    }

    updateStrategyDescription() {
        const queryStrategy = document.getElementById('queryStrategy');
        const simpleDesc = document.getElementById('simpleDesc');
        const multiDesc = document.getElementById('multiDesc');
        
        if (!queryStrategy || !simpleDesc || !multiDesc) return;
        
        const isMultiQuery = queryStrategy.value === 'multi';
        
        if (isMultiQuery) {
            simpleDesc.classList.add('hidden');
            multiDesc.classList.remove('hidden');
        } else {
            simpleDesc.classList.remove('hidden');
            multiDesc.classList.add('hidden');
        }
        
        // Update input hint if in analytics mode
        if (this.activeMode === 'analytics') {
            this.updateAnalyticsInputHint();
        }
    }

    updateAnalyticsInputHint() {
        const queryStrategy = document.getElementById('queryStrategy');
        if (!queryStrategy) return;
        
        const isMultiQuery = queryStrategy.value === 'multi';
        
        if (isMultiQuery) {
            this.elements.inputHint.textContent = '📊 Multi-Query: "Generate comprehensive business dashboard with sales and customer insights"';
        } else {
            this.elements.inputHint.textContent = '🚀 Simple Query: "Show me farmers earning less than $40 per month"';
        }
    }

    toggleConnectionSection() {
        const connectionForm = document.getElementById('connectionForm');
        const connectionToggle = document.getElementById('connectionToggle');
        
        if (!connectionForm || !connectionToggle) return;
        
        if (connectionForm.classList.contains('hidden')) {
            connectionForm.classList.remove('hidden');
            connectionToggle.style.transform = 'rotate(0deg)';
        } else {
            connectionForm.classList.add('hidden');
            connectionToggle.style.transform = 'rotate(-90deg)';
        }
    }

    updateConnectionIndicator(connected) {
        const connectionIndicator = document.getElementById('connectionIndicator');
        if (!connectionIndicator) return;
        
        if (connected) {
            connectionIndicator.classList.remove('hidden');
            connectionIndicator.textContent = '✓ Connected';
            connectionIndicator.className = 'text-xs px-2 py-1 bg-green-800 text-green-300 rounded-full';
        } else {
            connectionIndicator.classList.add('hidden');
        }
    }

    async testDatabaseConnection() {
        try {
            const dbType = this.elements.dbType.value;
            let connection;
            
            if (dbType === 'sqlite') {
                const dbPath = this.elements.dbPath.value.trim();
                if (!dbPath) {
                    this.showConnectionStatus('Please enter a database path', 'error');
                    return;
                }
                connection = {
                    db_type: dbType,
                    database: dbPath,
                    file_path: dbPath
                };
            } else if (dbType === 'postgresql') {
                const host = this.elements.pgHost.value.trim();
                const port = this.elements.pgPort.value.trim();
                const database = this.elements.pgDatabase.value.trim();
                const username = this.elements.pgUsername.value.trim();
                const schema = this.elements.pgSchema.value.trim();
                const password = this.elements.pgPassword.value;
                
                if (!host || !database || !username) {
                    this.showConnectionStatus('Please fill in all required PostgreSQL fields', 'error');
                    return;
                }
                
                connection = {
                    db_type: dbType,
                    host: host,
                    port: parseInt(port) || 5432,
                    database: database,
                    username: username,
                    password: password,
                    db_schema: schema || 'public'
                };
            } else {
                this.showConnectionStatus('Unsupported database type', 'error');
                return;
            }
            
            this.elements.testConnectionBtn.disabled = true;
            this.elements.testConnectionBtn.innerHTML = `
                <svg class="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Testing...
            `;
            
            const response = await fetch('/analytics/test-connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ connection })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.databaseConnection = connection;
                this.tables = result.tables || [];
                this.showConnectionStatus(`✅ Connected! Found ${result.tables ? result.tables.length : 0} tables`, 'success');
                this.updateTablesUI(result.tables || []);
                this.updateAnalyticsStats(true, result.tables ? result.tables.length : 0);
                
                // Auto-collapse connection section after successful connection
                setTimeout(() => {
                    const connectionForm = document.getElementById('connectionForm');
                    const connectionToggle = document.getElementById('connectionToggle');
                    if (connectionForm && connectionToggle) {
                        connectionForm.classList.add('hidden');
                        connectionToggle.style.transform = 'rotate(-90deg)';
                    }
                }, 2000);
            } else {
                this.showConnectionStatus(`❌ ${result.error || result.message}`, 'error');
                this.updateAnalyticsStats(false, 0);
            }
            
        } catch (error) {
            console.error('Connection test failed:', error);
            this.showConnectionStatus(`❌ Connection failed: ${error.message}`, 'error');
            this.updateAnalyticsStats(false, 0);
        } finally {
            this.elements.testConnectionBtn.disabled = false;
            this.elements.testConnectionBtn.innerHTML = `
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                Test Connection
            `;
        }
    }
    
    showConnectionStatus(message, type) {
        this.elements.connectionStatus.textContent = message;
        this.elements.connectionStatus.classList.remove('hidden', 'text-slate-400', 'text-green-400', 'text-red-400');
        
        switch(type) {
            case 'success':
                this.elements.connectionStatus.classList.add('text-green-400');
                this.updateConnectionIndicator(true);
                break;
            case 'error':
                this.elements.connectionStatus.classList.add('text-red-400');
                this.updateConnectionIndicator(false);
                break;
            default:
                this.elements.connectionStatus.classList.add('text-slate-400');
                this.updateConnectionIndicator(false);
        }
        
        setTimeout(() => {
            if (type !== 'success') {
                this.elements.connectionStatus.classList.add('hidden');
            }
        }, 5000);
    }
    
    updateTablesUI(tables) {
        if (tables.length === 0) {
            this.elements.tablesList.innerHTML = `
                <div class="text-center text-slate-500 py-4">
                    <svg class="mx-auto h-8 w-8 text-slate-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 1.79 4 4 4h8c2.21 0 4-1.79 4-4V7c0-2.21-1.79-4-4-4H8c-2.21 0-4 1.79-4 4z" />
                    </svg>
                    <p class="text-sm">No tables found</p>
                </div>
            `;
        } else {
            this.elements.tablesList.innerHTML = tables.map(table => `
                <div class="bg-slate-700 rounded-lg p-3 border border-slate-600 hover:border-slate-500 transition-colors">
                    <div class="flex items-center">
                        <svg class="w-4 h-4 mr-2 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2v2z" />
                        </svg>
                        <span class="text-sm font-medium text-white">${table}</span>
                    </div>
                </div>
            `).join('');
        }
    }
    
    updateAnalyticsStats(connected, tableCount) {
        this.elements.dbStatus.textContent = connected ? 'Connected' : 'Not Connected';
        this.elements.dbStatus.className = connected ? 'text-green-400' : 'text-red-400';
        this.elements.tablesCount.textContent = tableCount;
    }
    
    setSampleQuery(query) {
        this.elements.messageInput.value = query;
        this.elements.messageInput.style.height = 'auto';
        this.elements.messageInput.style.height = Math.min(this.elements.messageInput.scrollHeight, 120) + 'px';
        this.elements.messageInput.focus();
    }
    
    clearAnalytics() {
        this.elements.analyticsFrame.innerHTML = `
            <div class="text-center text-slate-400 mt-8 p-8">
                <svg class="w-16 h-16 mx-auto mb-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                </svg>
                <p class="text-lg font-medium">Database Analytics</p>
                <p class="text-sm mt-2">Connect to a database and ask analytical questions!</p>
                <p class="text-xs mt-1 text-slate-500">Example: "Show me farmers earning less than $40 per month"</p>
            </div>
        `;
        this.elements.openAnalyticsBtn.classList.add('hidden');
    }
    
    openAnalyticsInNewWindow() {
        // This would open the last analytics result in a new window
        // Implementation would depend on storing the last generated HTML
        alert('Feature coming soon! Analytics will open in a new window.');
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
        if (!message || this.isStreaming || this.isAnalyzing) return;
        
        if (this.activeMode === 'rag') {
            await this.sendRagMessage(message);
        } else if (this.activeMode === 'analytics') {
            await this.sendAnalyticsQuery(message);
        }
    }
    
    async sendRagMessage(message) {
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
    
    async sendAnalyticsQuery(message) {
        if (!this.databaseConnection) {
            alert('Please connect to a database first!');
            return;
        }

        // Clear input and reset height
        this.elements.messageInput.value = '';
        this.elements.messageInput.style.height = 'auto';

        // Get selected query strategy
        const queryStrategy = document.getElementById('queryStrategy').value;
        const isMultiQuery = queryStrategy === 'multi';

        // Set analyzing state with strategy indicator
        this.setAnalyzingState(true, isMultiQuery);

        try {
            // Choose endpoint based on strategy
            const endpoint = isMultiQuery ? '/analytics/generate-multi-query-html' : '/analytics/generate-html';
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    connection: this.databaseConnection,
                    user_query: message
                })
            });

            if (response.ok) {
                const htmlContent = await response.text();
                this.displayAnalyticsResult(htmlContent, isMultiQuery);
                this.elements.openAnalyticsBtn.classList.remove('hidden');
                this.elements.lastQueryTime.textContent = new Date().toLocaleTimeString();
                
                // Update analytics stats
                this.updateAnalyticsStats(isMultiQuery, message);
            } else {
                const errorText = await response.text();
                this.displayAnalyticsError(message, errorText, isMultiQuery);
            }

        } catch (error) {
            console.error('Analytics error:', error);
            this.displayAnalyticsError(message, error.message, isMultiQuery);
        } finally {
            this.setAnalyzingState(false);
        }
    }    displayAnalyticsResult(htmlContent, isMultiQuery = false) {
        // Create an iframe to safely display the HTML content
        const iframe = document.createElement('iframe');
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        iframe.style.backgroundColor = '#0f172a';
        
        // Add loading indicator for multi-query
        if (isMultiQuery) {
            iframe.title = 'Multi-Query Analytics Dashboard';
        } else {
            iframe.title = 'Analytics Dashboard';
        }
        
        this.elements.analyticsFrame.innerHTML = '';
        this.elements.analyticsFrame.appendChild(iframe);
        
        // Write the HTML content to the iframe
        iframe.contentDocument.open();
        iframe.contentDocument.write(htmlContent);
        iframe.contentDocument.close();
        
        // Show analytics container
        this.elements.analyticsContainer.classList.remove('hidden');
    }
    
    displayAnalyticsError(query, error, isMultiQuery = false) {
        const strategyText = isMultiQuery ? 'Multi-Query Analytics' : 'Simple Analytics';
        const strategyIcon = isMultiQuery ? '📊' : '🚀';
        
        this.elements.analyticsFrame.innerHTML = `
            <div class="flex items-center justify-center h-full p-8">
                <div class="text-center max-w-md">
                    <svg class="w-16 h-16 mx-auto mb-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                    </svg>
                    <h3 class="text-lg font-semibold text-white mb-2">${strategyIcon} ${strategyText} Error</h3>
                    <p class="text-sm text-slate-300 mb-4">Query: "${query}"</p>
                    <div class="text-sm text-red-400 bg-red-900 p-3 rounded mb-4">${error}</div>
                    ${isMultiQuery ? `
                    <div class="text-xs text-yellow-300 bg-yellow-900 p-2 rounded mb-4">
                        💡 Try using Simple Query strategy for this request
                    </div>
                    ` : ''}
                    <button onclick="ragApp.clearAnalytics()" class="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded transition-colors duration-200">
                        Clear & Try Again
                    </button>
                </div>
            </div>
        `;
        
        // Show analytics container
        this.elements.analyticsContainer.classList.remove('hidden');
    }

    updateAnalyticsStats(isMultiQuery, query) {
        const strategyText = isMultiQuery ? 'Multi-Query Strategy' : 'Simple Query Strategy';
        const strategyIcon = isMultiQuery ? '📊' : '🚀';
        
        // Ensure query is a string and handle safely
        const queryString = typeof query === 'string' ? query : String(query || '');
        const truncatedQuery = queryString.length > 50 ? queryString.substring(0, 50) + '...' : queryString;
        
        if (this.elements.analyticsStats) {
            this.elements.analyticsStats.innerHTML = `
                <div class="text-xs text-slate-400">
                    <p><span class="text-blue-300">${strategyIcon} Strategy:</span> ${strategyText}</p>
                    <p><span class="text-green-300">📝 Query:</span> ${truncatedQuery}</p>
                    <p><span class="text-yellow-300">⏰ Generated:</span> ${new Date().toLocaleTimeString()}</p>
                </div>
            `;
            this.elements.analyticsStats.classList.remove('hidden');
        }
    }

    setAnalyzingState(analyzing, isMultiQuery = false) {
        this.isAnalyzing = analyzing;
        
        if (analyzing) {
            this.elements.sendBtn.disabled = true;
            this.elements.sendIcon.classList.add('hidden');
            this.elements.sendSpinner.classList.remove('hidden');
            this.elements.streamingStatus.classList.remove('hidden');
            
            // Different messages based on query strategy
            if (isMultiQuery) {
                this.elements.streamingText.textContent = 'Generating multi-query analytics dashboard...';
            } else {
                this.elements.streamingText.textContent = 'Generating analytics...';
            }
        } else {
            this.elements.sendBtn.disabled = false;
            this.elements.sendIcon.classList.remove('hidden');
            this.elements.sendSpinner.classList.add('hidden');
            this.elements.streamingStatus.classList.add('hidden');
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

// Global functions for HTML onclick handlers
function toggleConnectionSection() {
    if (window.ragApp) {
        window.ragApp.toggleConnectionSection();
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.ragApp = new RAGChatApp();
});