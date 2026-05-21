# AI Radio Presenter System

Production-ready autonomous AI radio presenter system capable of running fully autonomous multi-hour broadcasts with intelligent segment management, natural language generation, and text-to-speech synthesis.

## 🎙️ Features

### Core Architecture
- **Autonomous Broadcast Loop** - Runs continuously without human intervention for 2-6 hour sessions
- **Show Planner** - Generates deterministic, structured show plans before execution
- **Director System** - Real-time autonomous decision-making for segment transitions and pacing
- **State Engine** - Persistent runtime memory with Redis + PostgreSQL
- **LLM Generator** - GPT-powered script generation with structured prompts
- **TTS Engine** - ElevenLabs voice synthesis with language support
- **Timing Engine** - Strict asyncio-based segment duration control

### Capabilities
- ✅ Multi-hour autonomous broadcasts (2-6 hours)
- ✅ Fluent speech via TTS with natural pacing
- ✅ Automatic segment transitions based on timing and engagement
- ✅ Context-aware show continuity
- ✅ Multilingual support (English, Swahili, code-switching)
- ✅ Energy level management and audience engagement simulation
- ✅ Real-time pause/resume capability
- ✅ Full state persistence and recovery

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI REST API                      │
│              (WebSocket for live control)                │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────┐
│              Radio Service (Orchestrator)                 │
│              - Show initialization                        │
│              - Broadcast management                       │
│              - State coordination                         │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌────────┐
    │ Show   │ │Director│ │Broadcast
    │Planner │ │System  │ │Loop
    └────────┘ └────────┘ └────────┐
                                    │
        ┌───────────────────────────┤
        ▼           ▼              ▼
    ┌────────┐  ┌────────┐  ┌──────────┐
    │  LLM   │  │ TTS    │  │ State    │
    │Generator│  │Engine │  │Engine    │
    └────────┘  └────────┘  └──────────┘
        │           │            │
    OpenAI    ElevenLabs    Redis/PostgreSQL
```

## 📋 System Components

### 1. **Show Planner** (`app/core/show_planner.py`)
Generates deterministic show structure before broadcast.

```python
from app.core.show_planner import show_planner

# Generate 3-hour show
show_plan = show_planner.generate_show_plan(
    duration_seconds=10800,
    show_name="The Morning Drive",
    primary_language="english",
    target_audience="professionals",
)
```

**Features:**
- Segment-based planning with flexible/optional segments
- Multiple show templates (1h, 2h, 3h, 6h)
- Duration normalization
- Language and mood assignment
- JSON serialization for persistence

### 2. **State Engine** (`app/core/state_engine.py`)
Persistent runtime state management with automatic failover.

```python
from app.core.state_engine import state_engine, ShowState

# Save state
await state_engine.save_state(show_state)

# Load state
state = await state_engine.load_state(show_id)
```

**Storage Hierarchy:**
1. Redis (primary) - Fast, distributed
2. PostgreSQL (fallback) - Persistent
3. In-Memory (development) - No external deps

### 3. **Director System** (`app/core/director.py`)
Autonomous decision-making for show flow management.

```python
from app.core.director import Director

director = Director(show_plan)
decision = director.decide_next_action(current_state)

# Possible decisions:
# - PROCEED_TO_NEXT: Move to next segment
# - EXTEND_CURRENT: Extend current segment
# - SHORTEN_CURRENT: Shorten due to time constraints
# - ADJUST_ENERGY: Change energy level
# - SWITCH_LANGUAGE: Switch to secondary language
# - INSERT_BREAK: Insert filler/ad
```

**Logic:**
- Time-based decisions (remaining show duration)
- Engagement-based adjustments (simulated or real metrics)
- Energy level management
- Language switching based on humor/sentiment

### 4. **LLM Generator** (`app/ai/llm_generator.py`)
OpenAI GPT-based script generation with structured prompts.

```python
from app.ai.llm_generator import get_llm_generator

llm = get_llm_generator()

context = SegmentPromptContext(
    segment_type="talk_segment",
    language="english",
    mood="humorous",
    energy_level=0.8,
    humor_level=0.6,
)

script = await llm.generate_segment_script(context)
```

**Key Features:**
- **Structured Prompts** - System + user prompts for consistency
- **Context Awareness** - Recent segment history, audience metrics
- **Language Policy** - Enforces correct language mixing
- **Duration Estimates** - Calculates read-time based on word count

### 5. **TTS Engine** (`app/voice/tts_engine.py`)
ElevenLabs voice synthesis with caching and multi-language support.

```python
from app.voice.tts_engine import get_tts_engine

tts = get_tts_engine()

audio = await tts.generate_audio(
    segment_id="seg_001",
    text=script_content,
    language="english",
    mood="professional",
    duration_estimate=300,
)
```

**Voices:**
- English: Professional, Friendly, Energetic, Calm
- Swahili: Native speaker variants
- Audio Caching: In-memory cache for repeated segments

### 6. **Broadcast Loop** (`app/core/broadcast_loop.py`)
Main runtime engine orchestrating all components.

```python
from app.core.broadcast_loop import BroadcastLoop

loop = BroadcastLoop(show_plan, state_engine)

await loop.initialize_show()
await loop.start_broadcast()

# Runs autonomously until completion or stop signal
```

**Main Loop:**
```
1. Check timing (remaining time)
2. Get director decision
3. Execute decision (adjust segment, switch language, etc.)
4. If new segment: Generate script → Synthesize audio
5. Update state & emit events
6. Sleep briefly
7. Repeat until broadcast_duration_reached
```

## 🚀 Quick Start

### Installation

```bash
# Clone repository
cd /path/to/RADIO\ AI\ gent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy example environment
cp .env.example .env

# Edit .env with your API keys
# OPENAI_API_KEY=sk-...
# ELEVENLABS_API_KEY=...
```

### Running Locally

```bash
# Start FastAPI server
python -m uvicorn main:app --reload

# API will be available at http://localhost:8000
# Documentation at http://localhost:8000/docs
```

## 📡 API Usage

### Create Show Plan

```bash
curl -X POST http://localhost:8000/api/v1/radio/show/create \
  -H "Content-Type: application/json" \
  -d '{
    "duration_hours": 3,
    "show_name": "The Morning Drive",
    "primary_language": "english",
    "target_audience": "professionals"
  }'
```

Response:
```json
{
  "show_id": "show_abc123xyz",
  "show_name": "The Morning Drive",
  "total_duration": 10800,
  "segments_count": 12,
  "primary_language": "english"
}
```

### Start Broadcast

```bash
curl -X POST http://localhost:8000/api/v1/radio/shows/start \
  -H "Content-Type: application/json" \
  -d '{
    "duration_hours": 3,
    "show_name": "The Morning Drive",
    "primary_language": "english",
    "target_audience": "professionals"
  }'
```

### Get Status

```bash
curl http://localhost:8000/api/v1/radio/shows/state/{show_id}
```

Response:
```json
{
  "show_id": "show_abc123xyz",
  "show_name": "The Morning Drive",
  "status": "running",
  "elapsed_time": 1200,
  "remaining_time": 9600,
  "current_segment_index": 2,
  "total_segments": 12,
  "segments_completed": 2,
  "energy_level": 0.65
}
```

### Control Broadcast

```bash
# Pause
curl -X POST http://localhost:8000/api/v1/radio/shows/pause/{show_id}

# Resume
curl -X POST http://localhost:8000/api/v1/radio/shows/resume/{show_id}

# Stop
curl -X POST http://localhost:8000/api/v1/radio/shows/stop/{show_id}
```

## 🧪 Example: Complete Broadcast Session

```python
import asyncio
from app.services.radio_service import get_radio_service
from app.core.broadcast_loop import BroadcastLoopEvent

async def run_broadcast():
    service = get_radio_service()
    
    # Initialize with API keys
    await service.initialize({
        "openai_api_key": "sk-...",
        "elevenlabs_api_key": "...",
    })
    
    # Create show plan
    show_plan = service.create_show_plan(
        duration_hours=3.0,
        show_name="AI Radio Test",
        primary_language="english",
        target_audience="general",
    )
    
    # Define event handler
    async def handle_event(event_type: BroadcastLoopEvent, data: dict):
        if event_type == BroadcastLoopEvent.SEGMENT_START:
            print(f"▶️  Starting: {data['segment_title']}")
        elif event_type == BroadcastLoopEvent.CONTENT_GENERATED:
            print(f"✍️  Generated: {data['word_count']} words")
        elif event_type == BroadcastLoopEvent.AUDIO_READY:
            print(f"🔊 Audio ready: {data['audio_size_bytes']} bytes")
        elif event_type == BroadcastLoopEvent.SEGMENT_COMPLETE:
            print(f"✅ Segment complete")
    
    # Start broadcast
    broadcast = await service.start_broadcast(
        show_plan,
        event_callback=handle_event,
    )
    
    # Monitor in real-time
    while True:
        status = await service.get_broadcast_status(show_plan.show_id)
        if status['status'] == 'completed':
            break
        
        print(f"Time: {status['elapsed_time']}s / "
              f"{status['remaining_time']}s remaining")
        await asyncio.sleep(5)

# Run
asyncio.run(run_broadcast())
```

## 🔧 Production Deployment

### Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build
docker build -t radio-ai .

# Run
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e ELEVENLABS_API_KEY=$ELEVENLABS_API_KEY \
  radio-ai
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: radio-ai
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: radio-ai
        image: radio-ai:latest
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai
        - name: REDIS_HOST
          value: redis-cluster.default
```

## 📊 Monitoring & Logging

### Logs
```bash
# Check logs
tail -f logs/broadcast.log

# Filter by component
grep "Director:" logs/broadcast.log
grep "LLM Generator:" logs/broadcast.log
grep "TTS Engine:" logs/broadcast.log
```

### Metrics
- Segment completion time
- LLM generation latency
- TTS synthesis duration
- Energy level trends
- Audience engagement metrics

## 🔐 Security Considerations

1. **API Keys** - Store in environment variables, never commit
2. **Rate Limiting** - Implement per-IP and per-show limits
3. **Input Validation** - Pydantic models validate all inputs
4. **CORS** - Configure allowed origins in production
5. **Logging** - Sanitize sensitive data in logs

## 🐛 Troubleshooting

### Redis Connection Failed
```
Solution: Ensure Redis is running on localhost:6379
docker run -d -p 6379:6379 redis:latest
```

### OpenAI API Errors
```
Solution: Check API key and rate limits
Set OPENAI_TEMPERATURE lower for more consistency
```

### TTS Latency
```
Solution: Use audio caching to speed up repeated segments
Check cache statistics: GET /api/v1/radio/cache-stats
```

## 📚 Documentation

See individual module docstrings for detailed API documentation.

## 📄 License

Proprietary - Production System

## 🙋 Support

For production deployment support and customization, contact the engineering team.
