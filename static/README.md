# Revolt Motors Voice Assistant

A real-time conversational voice interface built with Python, FastAPI, and the Gemini Live API. This application replicates the functionality of the Revolt Motors chatbot with natural voice interaction capabilities.

## Features

- ✅ **Real-time voice conversation** with low latency (1-2 seconds)
- ✅ **Interruption support** - Stop AI mid-response and ask new questions
- ✅ **Natural language processing** using Gemini Live API
- ✅ **Revolt Motors focused** - AI only discusses Revolt Motors products and services
- ✅ **Multi-language support** (inherited from Gemini)
- ✅ **Clean, responsive UI** with voice visualizations
- ✅ **Push-to-talk** functionality (spacebar)
- ✅ **Server-to-server architecture** for better performance

## Demo

The application provides:
- Natural conversation flow with Rev (Revolt Motors AI assistant)
- Real-time audio processing and response
- Interrupt capabilities during AI responses
- Visual feedback for recording and AI status
- Information about Revolt Motors bikes, pricing, features, and services

## Quick Setup

### Prerequisites

- Python 3.8 or higher
- A Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))
- Modern web browser with microphone access

### Installation

1. **Clone or create the project structure:**
```bash
mkdir revolt-voice-assistant
cd revolt-voice-assistant
```

2. **Create the required files** (copy the code from the artifacts above):
   - `main.py` - Main backend server
   - `static/app.js` - Frontend JavaScript
   - `requirements.txt` - Python dependencies
   - `.env` - Environment variables

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Get your Gemini API key:**
   - Visit https://aistudio.google.com
   - Create a free account
   - Generate an API key
   - Add it to your `.env` file:
```bash
GEMINI_API_KEY=your_actual_api_key_here
```

5. **Create the static directory:**
```bash
mkdir static
# Place app.js in the static directory
```

6. **Run the application:**
```bash
python main.py
```

7. **Open your browser:**
   - Navigate to `http://localhost:8000`
   - Allow microphone access when prompted
   - Wait for "Connected - Ready to chat!" status
   - Click the microphone button or hold spacebar to talk

## Usage Instructions

### Voice Interaction
- **Click the microphone button** to start/stop recording
- **Hold spacebar** for push-to-talk functionality
- **Click "Stop AI"** to interrupt the assistant mid-response
- **Wait for the green "Connected" status** before starting

### Example Conversations
Try asking Rev about:
- "Tell me about Revolt Motors"
- "What are the features of RV400?"
- "How much does the RV1+ cost?"
- "Where can I book a test ride?"
- "Tell me about the My Revolt Plan"
- "What's the range of your electric bikes?"

## Technical Architecture

### Backend (Python + FastAPI)
- **FastAPI** for the web server and API endpoints
- **WebSockets** for real-time client communication
- **Gemini Live API** integration via WebSocket
- **Audio processing** for PCM conversion
- **Session management** for multiple concurrent users

### Frontend (JavaScript)
- **WebRTC** for microphone access
- **MediaRecorder API** for audio capture
- **Web Audio API** for audio processing
- **WebSocket client** for real-time communication
- **Responsive UI** with visual feedback

### Data Flow
1. User speaks into microphone
2. Audio captured and converted to PCM format
3. Sent to backend via WebSocket
4. Backend forwards to Gemini Live API
5. Gemini processes and returns audio response
6. Backend streams response back to frontend
7. Frontend plays audio response

## Model Configuration

The application is configured to use:
- **Development**: `gemini-2.0-flash-live-001` (higher rate limits)
- **Production**: `gemini-2.5-flash-preview-native-audio-dialog` (better quality)

To switch models, edit the `model` field in `main.py`:
```python
"model": "models/gemini-2.5-flash-preview-native-audio-dialog"
```

## System Instructions

The AI is programmed with specific instructions to:
- Only discuss Revolt Motors products and services
- Provide accurate information about bike models, pricing, and features
- Maintain a conversational and helpful tone
- Keep responses concise for voice interaction
- Redirect off-topic questions back to Revolt Motors

## Troubleshooting

### Common Issues

**"Connection Failed" error:**
- Check your GEMINI_API_KEY in the `.env` file
- Ensure you have internet connectivity
- Verify the API key is valid

**"Microphone access denied":**
- Allow microphone permissions in your browser
- Use HTTPS in production (required for microphone access)
- Try refreshing the page after granting permissions

**High latency:**
- Check your internet connection
- Consider switching to the faster model for development
- Ensure you're not hitting API rate limits

**Audio not playing:**
- Check browser audio permissions
- Ensure speakers/headphones are connected
- Try refreshing the page

### Development Tips

1. **Monitor the console** for detailed logs and error messages
2. **Use browser dev tools** to inspect WebSocket messages
3. **Test with different audio inputs** to ensure robustness
4. **Monitor API usage** at aistudio.google.com to avoid rate limits

## API Rate Limits

Free tier limitations:
- **gemini-2.5-flash-preview-native-audio-dialog**: 10 requests/minute
- **gemini-2.0-flash-live-001**: 1000 requests/day

For production use, consider upgrading to a paid plan.

## Deployment

### Local Development
```bash
python main.py
```

### Production Deployment
For production deployment:
1. Use HTTPS (required for microphone access)
2. Set appropriate CORS settings
3. Configure proper logging
4. Use a production WSGI server like Gunicorn
5. Set up proper environment variable management

### Docker Deployment (Optional)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

## Contributing

This is a demonstration project. To extend functionality:
1. Modify system instructions in `main.py`
2. Add new UI features in `static/app.js`
3. Implement additional audio processing features
4. Add support for multiple languages

## License

This project is for educational and demonstration purposes.

## Support

For issues related to:
- **Gemini API**: Check the [official documentation](https://ai.google.dev/gemini-api/docs/live)
- **Audio processing**: Refer to Web Audio API documentation
- **FastAPI**: Check the FastAPI documentation

---

**Demo Video Requirements:**
Create a 30-60 second screen recording showing:
1. Opening the application and waiting for connection
2. Starting a natural conversation about Revolt Motors
3. Interrupting the AI mid-response (important!)
4. Demonstrating overall responsiveness and low latency

**Submission Checklist:**
- [ ] Application runs successfully
- [ ] Voice interaction works both ways
- [ ] Interruption feature functions correctly
- [ ] Low latency (1-2 seconds) achieved
- [ ] AI focused on Revolt Motors topics
- [ ] Demo video recorded and uploaded to Google Drive
- [ ] Code uploaded to GitHub with this README
