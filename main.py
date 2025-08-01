import asyncio
import json
import os
import logging
from typing import Optional
import base64
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Revolt Motors Voice Assistant")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Gemini Live API configuration
GEMINI_WS_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"

# System instructions for Revolt Motors
SYSTEM_INSTRUCTION = """You are Rev, the voice assistant for Revolt Motors - India's first AI-enabled electric motorcycle company. 

Key information about Revolt Motors:
- We manufacture premium electric motorcycles including RV400 and RV1+ models
- Our motorcycles feature AI-enabled technology and smart connectivity
- We have a subscription-based ownership model called "My Revolt Plan"
- Our bikes offer 0-80 kmph acceleration and long-range battery performance
- We have charging stations across major Indian cities
- Our mobile app allows remote bike control and monitoring
- Price range: RV1+ starts around ₹84,990, RV400 around ₹1.38 lakhs
- Available in multiple cities across India
- Key features: 3 riding modes, mobile app connectivity, portable battery

Guidelines:
- Keep responses conversational, helpful, and concise (2-3 sentences max)
- Focus only on Revolt Motors products, services, and related electric mobility topics
- If asked about competitors or unrelated topics, politely redirect to Revolt Motors
- Be enthusiastic about electric mobility and sustainable transportation
- Help with inquiries about pricing, features, test rides, and dealership locations
- Speak naturally as if you're a knowledgeable brand representative
- Use simple, clear language suitable for voice interaction"""

class GeminiLiveSession:
    def __init__(self, client_websocket: WebSocket):
        self.client_ws = client_websocket
        self.gemini_ws: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.session_id = str(id(self))
        
    async def connect_to_gemini(self):
        """Connect to Gemini Live API"""
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables")
            
            url = f"{GEMINI_WS_URL}?key={api_key}"
            logger.info(f"Connecting to Gemini Live API...")
            
            self.gemini_ws = await websockets.connect(url)
            self.is_connected = True
            
            # Setup the session
            await self.setup_session()
            
            # Notify client that connection is ready
            await self.client_ws.send_json({
                "type": "connection_status",
                "status": "connected"
            })
            
            logger.info("Successfully connected to Gemini Live API")
            
            # Start listening to Gemini responses
            asyncio.create_task(self.listen_to_gemini())
            
        except Exception as e:
            logger.error(f"Failed to connect to Gemini: {e}")
            await self.client_ws.send_json({
                "type": "error",
                "message": f"Failed to connect to AI service: {str(e)}"
            })
    
    async def setup_session(self):
        """Initialize the Gemini session with system instructions"""
        setup_message = {
            "setup": {
                "model": "models/gemini-2.0-flash-live-001",  # Use this for development
                # "model": "models/gemini-2.5-flash-preview-native-audio-dialog",  # Switch for production
                "generation_config": {
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": "Aoede"
                            }
                        }
                    }
                },
                "system_instruction": {
                    "parts": [{"text": SYSTEM_INSTRUCTION}]
                }
            }
        }
        
        await self.gemini_ws.send(json.dumps(setup_message))
        logger.info("Session setup sent to Gemini")
    
    async def listen_to_gemini(self):
        """Listen for messages from Gemini and forward to client"""
        try:
            async for message in self.gemini_ws:
                try:
                    data = json.loads(message)
                    await self.handle_gemini_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Gemini message: {e}")
                except Exception as e:
                    logger.error(f"Error handling Gemini message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("Gemini WebSocket connection closed")
            self.is_connected = False
            await self.client_ws.send_json({
                "type": "connection_status",
                "status": "disconnected"
            })
        except Exception as e:
            logger.error(f"Error in Gemini listener: {e}")
    
    async def handle_gemini_message(self, message):
        """Handle messages received from Gemini"""
        if "serverContent" in message:
            server_content = message["serverContent"]
            
            if "modelTurn" in server_content:
                parts = server_content["modelTurn"]["parts"]
                
                for part in parts:
                    if "inlineData" in part and part["inlineData"]["mimeType"] == "audio/pcm":
                        # Forward audio data to client
                        await self.client_ws.send_json({
                            "type": "audio_response",
                            "audio_data": part["inlineData"]["data"]
                        })
                    elif "text" in part:
                        # Forward text response to client
                        await self.client_ws.send_json({
                            "type": "text_response",
                            "text": part["text"]
                        })
            
            elif "turnComplete" in server_content:
                # Notify client that AI has finished speaking
                await self.client_ws.send_json({
                    "type": "turn_complete"
                })
        
        elif "setupComplete" in message:
            logger.info("Gemini setup completed")
            await self.client_ws.send_json({
                "type": "setup_complete"
            })
    
    async def send_audio_to_gemini(self, audio_data: str):
        """Send audio data to Gemini"""
        if not self.is_connected or not self.gemini_ws:
            logger.error("Not connected to Gemini")
            return
        
        try:
            message = {
                "clientContent": {
                    "turns": [{
                        "role": "user",
                        "parts": [{
                            "inlineData": {
                                "mimeType": "audio/pcm",
                                "data": audio_data
                            }
                        }]
                    }],
                    "turnComplete": True
                }
            }
            
            await self.gemini_ws.send(json.dumps(message))
            logger.info("Audio sent to Gemini")
            
        except Exception as e:
            logger.error(f"Failed to send audio to Gemini: {e}")
    
    async def send_text_to_gemini(self, text: str):
        """Send text data to Gemini"""
        if not self.is_connected or not self.gemini_ws:
            logger.error("Not connected to Gemini")
            return
        
        try:
            message = {
                "clientContent": {
                    "turns": [{
                        "role": "user",
                        "parts": [{
                            "text": text
                        }]
                    }],
                    "turnComplete": True
                }
            }
            
            await self.gemini_ws.send(json.dumps(message))
            logger.info(f"Text sent to Gemini: {text}")
            
        except Exception as e:
            logger.error(f"Failed to send text to Gemini: {e}")
    
    async def interrupt_gemini(self):
        """Send interrupt signal to Gemini"""
        if not self.is_connected or not self.gemini_ws:
            return
        
        try:
            message = {
                "clientContent": {
                    "turnComplete": False
                }
            }
            await self.gemini_ws.send(json.dumps(message))
            logger.info("Interrupt sent to Gemini")
        except Exception as e:
            logger.error(f"Failed to send interrupt: {e}")
    
    async def close(self):
        """Close the Gemini connection"""
        if self.gemini_ws:
            await self.gemini_ws.close()
        self.is_connected = False

# Store active sessions
active_sessions = {}

@app.get("/")
async def get_frontend():
    """Serve the frontend HTML"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Revolt Motors Voice Assistant</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .container {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                text-align: center;
                max-width: 500px;
                width: 90%;
            }
            
            .logo {
                width: 150px;
                height: 60px;
                margin: 0 auto 30px;
                background: linear-gradient(45deg, #ff6b6b, #ee5a24);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 18px;
            }
            
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 28px;
            }
            
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 16px;
            }
            
            .status {
                padding: 10px 20px;
                border-radius: 25px;
                margin-bottom: 30px;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            
            .status.connecting {
                background: #fff3cd;
                color: #856404;
            }
            
            .status.connected {
                background: #d4edda;
                color: #155724;
            }
            
            .status.disconnected {
                background: #f8d7da;
                color: #721c24;
            }
            
            .voice-button {
                width: 120px;
                height: 120px;
                border-radius: 50%;
                border: none;
                background: linear-gradient(45deg, #ff6b6b, #ee5a24);
                color: white;
                font-size: 24px;
                cursor: pointer;
                transition: all 0.3s ease;
                margin: 20px;
                box-shadow: 0 10px 30px rgba(238, 90, 36, 0.3);
            }
            
            .voice-button:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(238, 90, 36, 0.4);
            }
            
            .voice-button:active {
                transform: translateY(-2px);
            }
            
            .voice-button.recording {
                background: linear-gradient(45deg, #ff4757, #c44569);
                animation: pulse 1.5s infinite;
            }
            
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            
            .controls {
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-top: 30px;
            }
            
            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            
            .btn-secondary {
                background: #6c757d;
                color: white;
            }
            
            .btn-secondary:hover {
                background: #5a6268;
                transform: translateY(-2px);
            }
            
            .response-area {
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                min-height: 100px;
                text-align: left;
            }
            
            .audio-visualizer {
                height: 60px;
                background: #f0f0f0;
                border-radius: 10px;
                margin: 20px 0;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #666;
            }
            
            .wave {
                width: 4px;
                height: 20px;
                background: #ff6b6b;
                margin: 0 2px;
                border-radius: 2px;
                animation: wave 1s infinite ease-in-out;
            }
            
            .wave:nth-child(2) { animation-delay: 0.1s; }
            .wave:nth-child(3) { animation-delay: 0.2s; }
            .wave:nth-child(4) { animation-delay: 0.3s; }
            .wave:nth-child(5) { animation-delay: 0.4s; }
            
            @keyframes wave {
                0%, 40%, 100% { transform: scaleY(0.4); }
                20% { transform: scaleY(1); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">REVOLT</div>
            <h1>Voice Assistant</h1>
            <p class="subtitle">Talk to Rev about Revolt Motors</p>
            
            <div id="status" class="status connecting">Connecting...</div>
            
            <button id="voiceButton" class="voice-button" disabled>
                🎤
            </button>
            
            <div class="audio-visualizer" id="visualizer" style="display: none;">
                <div class="wave"></div>
                <div class="wave"></div>
                <div class="wave"></div>
                <div class="wave"></div>
                <div class="wave"></div>
            </div>
            
            <div class="controls">
                <button id="interruptButton" class="btn btn-secondary">Stop AI</button>
            </div>
            
            <div class="response-area" id="responseArea">
                <p>Click the microphone button and start talking about Revolt Motors!</p>
            </div>
        </div>
        
        <script src="/static/app.js"></script>
    </body>
    </html>
    """)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Create a new Gemini session for this client
    session = GeminiLiveSession(websocket)
    active_sessions[id(session)] = session
    
    try:
        # Connect to Gemini Live API
        await session.connect_to_gemini()
        
        # Handle client messages
        async for message in websocket.iter_json():
            message_type = message.get("type")
            
            if message_type == "audio_data":
                await session.send_audio_to_gemini(message["data"])
            elif message_type == "text_data":
                await session.send_text_to_gemini(message["data"])
            elif message_type == "interrupt":
                await session.interrupt_gemini()
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Clean up
        await session.close()
        if id(session) in active_sessions:
            del active_sessions[id(session)]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "active_sessions": len(active_sessions)}

if __name__ == "__main__":
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY environment variable is required!")
        print("Get your API key from: https://aistudio.google.com")
        exit(1)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
