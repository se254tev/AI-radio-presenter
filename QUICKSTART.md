# Quick Start Guide - AI Radio Presenter System

## 🚀 Get Up and Running in 5 Minutes

### Option 1: Local Development (Recommended for testing)

#### Prerequisites
- Python 3.11+
- Redis (optional, uses in-memory fallback)
- API keys for OpenAI and ElevenLabs (optional for testing)

#### Setup

```bash
# 1. Navigate to project
cd "c:/Users/SHARON Otunga/Desktop/RADIO AI gent"

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (optional)
cp .env.example .env
# Edit .env with your API keys (or leave empty for mock mode)

# 5. Run FastAPI server
python -m uvicorn main:app --reload

# 6. Visit API documentation
# http://localhost:8000/docs
```

### Option 2: Docker Compose (Full Stack with Redis + PostgreSQL)

```bash
# 1. Start all services
docker-compose up -d

# 2. Check logs
docker-compose logs -f app

# 3. Access API
# http://localhost:8000/docs

# 4. Stop services
docker-compose down
```

### Option 3: Standalone Docker

```bash
# Build image
docker build -t radio-ai .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e ELEVENLABS_API_KEY=your_key \
  radio-ai
```

## 📡 Basic Usage

### 1. Create a Show Plan

```bash
curl -X POST http://localhost:8000/api/v1/radio/show/create \
  -H "Content-Type: application/json" \
  -d '{
    "duration_hours": 1.0,
    "show_name": "My First AI Show",
    "primary_language": "english",
    "target_audience": "tech enthusiasts"
  }'
```

Response:
```json
{
  "show_id": "show_abc123xyz",
  "show_name": "My First AI Show",
  "total_duration": 3600,
  "segments_count": 8,
  "primary_language": "english"
}
```

### 2. Start Autonomous Broadcast

```bash
curl -X POST http://localhost:8000/api/v1/radio/shows/start \
  -H "Content-Type: application/json" \
  -d '{
    "duration_hours": 1.0,
    "show_name": "My First AI Show",
    "primary_language": "english",
    "target_audience": "tech enthusiasts"
  }'
```

### 3. Check Status

```bash
curl http://localhost:8000/api/v1/radio/shows/state/show_abc123xyz
```

### 4. Control Broadcast

```bash
# Pause
curl -X POST http://localhost:8000/api/v1/radio/show/show_abc123xyz/control \
  -H "Content-Type: application/json" \
  -d '{"action": "pause"}'

# Resume
curl -X POST http://localhost:8000/api/v1/radio/show/show_abc123xyz/control \
  -H "Content-Type: application/json" \
  -d '{"action": "resume"}'

# Stop
curl -X POST http://localhost:8000/api/v1/radio/show/show_abc123xyz/control \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'
```

## 🧪 Run Demonstrations

```bash
# Demo script shows all features
python demo.py
```

This demonstrates:
1. Show plan generation
2. Director decision-making
3. State persistence
4. Complete broadcast execution

## 📁 Project Structure

```
RADIO AI gent/
├── app/
│   ├── core/                 # Core engine
│   │   ├── show_planner.py   # Generate show structure
│   │   ├── state_engine.py   # Runtime state management
│   │   ├── director.py       # Autonomous decisions
│   │   └── broadcast_loop.py # Main execution loop
│   ├── ai/                   # AI integration
│   │   └── llm_generator.py  # Script generation
│   ├── voice/                # Voice synthesis
│   │   └── tts_engine.py     # Audio generation
│   ├── services/             # High-level services
│   │   └── radio_service.py  # Orchestration
│   └── api/                  # REST API
│       └── routes.py         # Endpoints
├── config.py                 # Configuration
├── main.py                   # FastAPI entry point
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container definition
├── docker-compose.yml        # Local stack
├── README.md                 # Full documentation
├── ARCHITECTURE.md           # System architecture
└── demo.py                   # Demonstration script
```

## 🔑 Key Concepts

### Show Planner
- Generates deterministic show structure before execution
- Creates segments with specific timing, mood, and language
- Outputs JSON-serializable ShowPlan

### Director
- Makes autonomous decisions in real-time
- Never generates content
- Decides: segment transitions, pacing adjustments, language switching
- Based on: remaining time, engagement metrics, energy levels

### State Engine
- Persists show state to Redis (primary) or PostgreSQL (fallback)
- Tracks: timing, segments completed, audience metrics
- Enables state recovery on restart

### LLM Generator
- Uses OpenAI GPT to create radio scripts
- Structured prompts for consistency
- Receives context from Director
- Does NOT make show-level decisions

### TTS Engine
- Converts scripts to speech using ElevenLabs
- Supports: English, Swahili, mood-based voice selection
- Audio caching for performance

### Broadcast Loop
- Main execution engine
- Orchestrates all components
- Runs autonomously until show ends
- Emits events for monitoring

## 🔧 Configuration

Key environment variables:

```bash
# Application
ENVIRONMENT=development
DEBUG=false

# APIs
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...

# Storage
REDIS_HOST=localhost
DATABASE_URL=postgresql://user:pass@localhost:5432/radio_ai

# Broadcast
MAX_SEGMENT_DURATION=600  # Max seconds per segment
ENABLE_AUDIO=true
DEFAULT_LANGUAGE=english
```

## 📊 Monitoring

### API Endpoints

- `GET /` - Root endpoint
- `GET /api/v1/radio/health` - Health check
- `POST /api/v1/radio/show/create` - Create show plan
- `POST /api/v1/radio/show/{id}/start` - Start broadcast
- `GET /api/v1/radio/show/{id}/status` - Get status
- `POST /api/v1/radio/show/{id}/control` - Control (pause/resume/stop)
- `GET /api/v1/radio/broadcasts` - List all broadcasts
- `GET /api/v1/radio/analytics/{id}` - Get analytics

### Logs

```bash
# Check main logs
tail -f logs/broadcast.log

# Filter by component
grep "Director:" logs/broadcast.log
grep "LLM Generator:" logs/broadcast.log
grep "TTS Engine:" logs/broadcast.log
```

## 🐛 Troubleshooting

### "Connection refused" on localhost:8000
```
Solution: Ensure FastAPI is running
python -m uvicorn main:app --reload
```

### Mock audio instead of real TTS
```
Solution: Set ELEVENLABS_API_KEY in .env
Default behavior uses mock for testing
```

### Redis connection error
```
Solution: Redis is optional, system uses in-memory fallback
To use Redis: docker-compose up redis
Or install locally: https://redis.io/download
```

### "No module named 'app'"
```
Solution: Run from project root directory
cd "c:/Users/SHARON Otunga/Desktop/RADIO AI gent"
```

## 📖 Next Steps

1. **Review Architecture**: Read ARCHITECTURE.md for deep technical details
2. **Customize Shows**: Modify `app/core/show_planner.py` templates
3. **Tune Director**: Adjust decision logic in `app/core/director.py`
4. **Integrate APIs**: Add real weather, news, listener data
5. **Deploy**: Use docker-compose or Kubernetes

## 💡 Example: Complete 3-Hour Broadcast

```python
import asyncio
from app.services.radio_service import get_radio_service

async def run_3_hour_show():
    service = get_radio_service()
    
    # Initialize
    await service.initialize({
        "openai_api_key": "your_key",
        "elevenlabs_api_key": "your_key",
    })
    
    # Create show
    show = service.create_show_plan(
        duration_hours=3.0,
        show_name="The Morning Drive",
        primary_language="english",
    )
    
    # Start (runs autonomously)
    broadcast = await service.start_broadcast(show)
    
    # Monitor
    while True:
        status = await service.get_broadcast_status(show.show_id)
        if status['status'] == 'completed':
            print(f"✅ Show completed! {status['segments_completed']} segments")
            break
        print(f"⏱️  {status['elapsed_time']}s elapsed")
        await asyncio.sleep(5)

asyncio.run(run_3_hour_show())
```

## 🎯 Success Criteria

Your system is working when:
✅ `GET /api/v1/radio/health` returns 200
✅ Create show plan returns show_id
✅ Start broadcast doesn't error
✅ Status updates show segments completing
✅ Audio files are generated in logs
✅ Director is making decisions
✅ Show completes without intervention

## 📞 Support

- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Architecture Guide**: See ARCHITECTURE.md
- **Code Examples**: See demo.py

---

**You're ready to launch autonomous AI radio broadcasts! 🚀🎙️**
