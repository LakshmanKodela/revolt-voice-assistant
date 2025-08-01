class VoiceAssistant {
    constructor() {
        this.ws = null;
        this.mediaRecorder = null;
        this.audioContext = null;
        this.isRecording = false;
        this.isConnected = false;
        this.audioChunks = [];
        
        // UI elements
        this.statusEl = document.getElementById('status');
        this.voiceButton = document.getElementById('voiceButton');
        this.interruptButton = document.getElementById('interruptButton');
        this.responseArea = document.getElementById('responseArea');
        this.visualizer = document.getElementById('visualizer');
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.connectWebSocket();
        await this.setupAudio();
    }
    
    setupEventListeners() {
        this.voiceButton.addEventListener('click', () => {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                this.startRecording();
            }
        });
        
        this.interruptButton.addEventListener('click', () => {
            this.interrupt();
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !e.repeat) {
                e.preventDefault();
                if (!this.isRecording) {
                    this.startRecording();
                }
            }
        });
        
        document.addEventListener('keyup', (e) => {
            if (e.code === 'Space') {
                e.preventDefault();
                if (this.isRecording) {
                    this.stopRecording();
                }
            }
        });
    }
    
    async connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.updateStatus('Connecting to AI...', 'connecting');
            };
            
            this.ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.updateStatus('Disconnected', 'disconnected');
                this.voiceButton.disabled = true;
                
                // Attempt to reconnect after 3 seconds
                setTimeout(() => this.connectWebSocket(), 3000);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateStatus('Connection Error', 'disconnected');
            };
            
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            this.updateStatus('Connection Failed', 'disconnected');
        }
    }
    
    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'connection_status':
                if (message.status === 'connected') {
                    this.isConnected = true;
                    this.updateStatus('Connected - Ready to chat!', 'connected');
                    this.voiceButton.disabled = false;
                } else {
                    this.isConnected = false;
                    this.updateStatus('Disconnected', 'disconnected');
                    this.voiceButton.disabled = true;
                }
                break;
                
            case 'setup_complete':
                console.log('AI setup completed');
                break;
                
            case 'audio_response':
                this.playAudioResponse(message.audio_data);
                break;
                
            case 'text_response':
                this.displayTextResponse(message.text);
                break;
                
            case 'turn_complete':
                console.log('AI finished speaking');
                this.hideVisualizer();
                break;
                
            case 'error':
                console.error('Server error:', message.message);
                this.displayError(message.message);
                break;
                
            case 'pong':
                // Keep-alive response
                break;
                
            default:
                console.log('Unknown message type:', message.type);
        }
    }
    
    async setupAudio() {
        try {
            // Request microphone permission
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                } 
            });
            
            // Create audio context for processing
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });
            
            // Setup MediaRecorder for audio capture
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.processRecordedAudio();
            };
            
            console.log('Audio setup completed');
            
        } catch (error) {
            console.error('Failed to setup audio:', error);
            this.displayError('Microphone access denied. Please allow microphone access and refresh the page.');
        }
    }
    
    startRecording() {
        if (!this.isConnected || !this.mediaRecorder) {
            console.log('Cannot start recording: not connected or no media recorder');
            return;
        }
        
        if (this.mediaRecorder.state === 'recording') {
            return;
        }
        
        this.audioChunks = [];
        this.isRecording = true;
        
        // Update UI
        this.voiceButton.classList.add('recording');
        this.voiceButton.innerHTML = '🔴';
        this.showVisualizer();
        this.updateResponse('Listening...');
        
        // Start recording
        this.mediaRecorder.start(100); // Collect data every 100ms
        
        console.log('Started recording');
    }
    
    stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) {
            return;
        }
        
        this.isRecording = false;
        
        // Update UI
        this.voiceButton.classList.remove('recording');
        this.voiceButton.innerHTML = '🎤';
        this.updateResponse('Processing...');
        
        // Stop recording
        if (this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
        }
        
        console.log('Stopped recording');
    }
    
    async processRecordedAudio() {
        if (this.audioChunks.length === 0) {
            return;
        }
        
        try {
            // Create blob from recorded chunks
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            
            // Convert to array buffer
            const arrayBuffer = await audioBlob.arrayBuffer();
            
            // Convert to base64 PCM
            const audioData = await this.convertToPCM(arrayBuffer);
            
            // Send to server
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    type: 'audio_data',
                    data: audioData
                }));
                
                this.updateResponse('Rev is thinking...');
            }
            
        } catch (error) {
            console.error('Failed to process audio:', error);
            this.displayError('Failed to process audio recording');
        }
    }
    
    async convertToPCM(arrayBuffer) {
        try {
            // Decode audio data
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            
            // Get PCM data (16-bit, 16kHz, mono)
            const pcmData = audioBuffer.getChannelData(0);
            
            // Convert to 16-bit PCM
            const pcm16 = new Int16Array(pcmData.length);
            for (let i = 0; i < pcmData.length; i++) {
                pcm16[i] = Math.max(-32768, Math.min(32767, pcmData[i] * 32768));
            }
            
            // Convert to base64
            const bytes = new Uint8Array(pcm16.buffer);
            let binary = '';
            for (let i = 0; i < bytes.length; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            
            return btoa(binary);
            
        } catch (error) {
            console.error('Audio conversion error:', error);
            throw error;
        }
    }
    
    async playAudioResponse(base64AudioData) {
        try {
            // Convert base64 to array buffer
            const binaryString = atob(base64AudioData);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            // Create audio buffer from PCM data
            const audioBuffer = this.audioContext.createBuffer(1, bytes.length / 2, 16000);
            const channelData = audioBuffer.getChannelData(0);
            
            // Convert 16-bit PCM to float
            const pcm16 = new Int16Array(bytes.buffer);
            for (let i = 0; i < pcm16.length; i++) {
                channelData[i] = pcm16[i] / 32768;
            }
            
            // Play audio
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            source.start();
            
            this.showVisualizer();
            this.updateResponse('Rev is speaking...');
            
        } catch (error) {
            console.error('Failed to play audio:', error);
        }
    }
    
    displayTextResponse(text) {
        this.updateResponse(`Rev: ${text}`);
    }
    
    displayError(error) {
        this.updateResponse(`Error: ${error}`);
    }
    
    interrupt() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'interrupt' }));
            this.updateResponse('Interrupted');
            this.hideVisualizer();
        }
    }
    
    updateStatus(message, type) {
        this.statusEl.textContent = message;
        this.statusEl.className = `status ${type}`;
    }
    
    updateResponse(message) {
        this.responseArea.innerHTML = `<p>${message}</p>`;
    }
    
    showVisualizer() {
        this.visualizer.style.display = 'flex';
    }
    
    hideVisualizer() {
        this.visualizer.style.display = 'none';
    }
    
    // Keep connection alive
    startKeepAlive() {
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); // Ping every 30 seconds
    }
}

// Initialize the voice assistant when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const assistant = new VoiceAssistant();
    assistant.startKeepAlive();
    
    // Add some helpful instructions
    console.log('Voice Assistant Controls:');
    console.log('- Click microphone button to start/stop recording');
    console.log('- Hold spacebar to record (push-to-talk)');
    console.log('- Click "Stop AI" to interrupt the assistant');
});
