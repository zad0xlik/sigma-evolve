/**
 * Worker Logs Component
 * 
 * Real-time streaming logs from SIGMA workers using Server-Sent Events (SSE).
 * Displays live worker activity with auto-scrolling terminal-like interface.
 */

export function createWorkerLogsComponent() {
    return {
        // State
        logs: [],
        connected: false,
        eventSource: null,
        autoScroll: true,
        filterLevel: 'all',
        filterWorker: 'all',
        maxLogs: 500,
        
        // Initialization
        init() {
            console.log('Initializing Worker Logs component');
            this.connectStream();
            
            // Auto-reconnect on visibility change
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden && !this.connected) {
                    console.log('Page visible again, reconnecting...');
                    this.connectStream();
                }
            });
        },
        
        // Connect to SSE stream
        connectStream() {
            if (this.eventSource) {
                this.eventSource.close();
            }
            
            console.log('Connecting to worker logs stream...');
            this.eventSource = new EventSource('/api/agents/logs/stream');
            
            this.eventSource.onopen = () => {
                console.log('✅ Connected to worker logs stream');
                this.connected = true;
            };
            
            this.eventSource.onmessage = (event) => {
                try {
                    const log = JSON.parse(event.data);
                    
                    // Skip connection messages
                    if (log.type === 'connected') {
                        return;
                    }
                    
                    this.addLog(log);
                } catch (error) {
                    console.error('Error parsing log event:', error);
                }
            };
            
            this.eventSource.onerror = (error) => {
                console.error('❌ SSE connection error:', error);
                this.connected = false;
                
                // Auto-reconnect after 5 seconds
                setTimeout(() => {
                    if (!this.connected) {
                        console.log('Attempting to reconnect...');
                        this.connectStream();
                    }
                }, 5000);
            };
        },
        
        // Disconnect from stream
        disconnect() {
            if (this.eventSource) {
                this.eventSource.close();
                this.eventSource = null;
                this.connected = false;
                console.log('Disconnected from worker logs stream');
            }
        },
        
        // Add log to buffer
        addLog(log) {
            // Add to logs array
            this.logs.push(log);
            
            // Trim logs if exceeds max
            if (this.logs.length > this.maxLogs) {
                this.logs.shift();
            }
            
            // Auto-scroll if enabled
            if (this.autoScroll) {
                this.$nextTick(() => {
                    const container = this.$refs.logsContainer;
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                    }
                });
            }
        },
        
        // Get filtered logs
        get filteredLogs() {
            return this.logs.filter(log => {
                // Filter by level
                if (this.filterLevel !== 'all' && log.level !== this.filterLevel) {
                    return false;
                }
                
                // Filter by worker
                if (this.filterWorker !== 'all' && log.worker !== this.filterWorker) {
                    return false;
                }
                
                return true;
            });
        },
        
        // Get unique workers from logs
        get workers() {
            const workerSet = new Set(this.logs.map(log => log.worker));
            return Array.from(workerSet).sort();
        },
        
        // Clear logs
        clearLogs() {
            this.logs = [];
        },
        
        // Format timestamp
        formatTime(timestamp) {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('en-US', { 
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        },
        
        // Get log level color class
        getLevelClass(level) {
            const classes = {
                'info': 'text-blue-400',
                'warning': 'text-yellow-400',
                'error': 'text-red-400',
                'debug': 'text-gray-400',
                'experiment': 'text-purple-400'
            };
            return classes[level] || 'text-gray-300';
        },
        
        // Get log level icon
        getLevelIcon(level) {
            const icons = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'debug': '🔍',
                'experiment': '🧪'
            };
            return icons[level] || '📝';
        },
        
        // Get worker badge color
        getWorkerBadgeClass(worker) {
            const colors = {
                'analysis': 'bg-blue-900 text-blue-300',
                'dream': 'bg-purple-900 text-purple-300',
                'recall': 'bg-green-900 text-green-300',
                'learning': 'bg-yellow-900 text-yellow-300',
                'think': 'bg-pink-900 text-pink-300'
            };
            return colors[worker] || 'bg-gray-900 text-gray-300';
        },
        
        // Export logs to file
        exportLogs() {
            const data = JSON.stringify(this.filteredLogs, null, 2);
            const blob = new Blob([data], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `worker-logs-${new Date().toISOString()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        },
        
        // Toggle auto-scroll
        toggleAutoScroll() {
            this.autoScroll = !this.autoScroll;
        },
        
        // Cleanup on destroy
        destroy() {
            this.disconnect();
        }
    };
}
