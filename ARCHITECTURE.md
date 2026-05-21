# AI Radio Presenter - Architecture Document

## System Overview

This document provides a deep dive into the architecture of the production-ready autonomous AI radio presenter system.

## 1. Design Principles

### Separation of Concerns
- **Show Planning** - Deterministic pre-execution structure
- **State Management** - Persistent runtime memory
- **Decision Making** - Director autonomous logic
- **Content Generation** - LLM responsibility only
- **Voice Synthesis** - TTS responsibility only
- **Timing Control** - AsyncIO strict enforcement

### No User Intervention
- The system runs completely autonomously once started
- No user prompts during execution
- Director makes all show-flow decisions
- Timing is enforced externally (not by LLM)

### Resilience
- State persistence allows recovery from failures
- Redis with PostgreSQL fallback
- In-memory storage for development
- Graceful degradation when APIs fail (mock data)

## 2. Core Components Deep Dive

### 2.1 Show Planner

**Responsibilities:**
- Generate deterministic show structure
- Create segment definitions with timing
- Assign mood, language, and context per segment
- Normalize durations to fit total show time

**Key Classes:**
```python
class ShowPlan:
    """Complete show blueprint"""
    show_id: str
    segments: List[Segment]
    total_duration: int
    primary_language: str
    secondary_language: str

class Segment:
    """Individual segment definition"""
    segment_type: SegmentType  # intro, music, talk, news, etc.
    duration: int
    mood: Mood  # energetic, calm, humorous, serious
    language: str
    is_flexible: bool  # Can be extended/shortened
    optional: bool  # Can be skipped
```

**Template System:**
- 1-hour, 2-hour, 3-hour, 6-hour templates
- Segment variety (music, talk, news, ads, interaction)
- Flexible duration normalization

**Example Flow:**
```
1. generate_show_plan(duration=3 hours)
2. Load 3-hour template
3. Create segments from template
4. Normalize all durations to exactly 3 hours
5. Return ready-to-execute ShowPlan
```

### 2.2 State Engine

**Responsibilities:**
- Track show execution state in real-time
- Persist state to Redis/PostgreSQL
- Support state recovery on restart
- Manage audience metrics
- Track segment history

**Storage Strategy:**
```
Primary: Redis
├─ Key: show_state:{show_id}
├─ TTL: 24 hours
└─ Fast access for active broadcasts

Fallback: PostgreSQL
├─ Append-only log
├─ Segment execution records
└─ Historical analytics

Tertiary: In-Memory
├─ Development/testing
└─ No external dependencies
```

**Key Classes:**
```python
class ShowState:
    """Runtime state during broadcast"""
    show_id: str
    status: BroadcastStatus  # running, paused, completed
    current_segment_index: int
    elapsed_time: int
    remaining_time: int
    segment_history: List[SegmentExecution]
    audience_metrics: AudienceMetrics
    energy_level: float
    language_mix_level: float
```

**State Update Frequency:** Every 1 second (configurable)

### 2.3 Director System

**Responsibilities:**
- Monitor show state continuously
- Make real-time autonomous decisions
- Never manage content generation
- Never manage timing details
- Adjust show flow based on:
  - Time remaining
  - Audience engagement
  - Energy levels
  - Segment completion

**Decision Types:**
```python
class DirectorDecision(Enum):
    PROCEED_TO_NEXT = "Go to next segment"
    EXTEND_CURRENT = "Add more time to current"
    SHORTEN_CURRENT = "Cut current segment short"
    INSERT_BREAK = "Add filler/ad break"
    SKIP_SEGMENT = "Skip optional segment"
    ADJUST_ENERGY = "Boost or reduce energy"
    SWITCH_LANGUAGE = "Change to secondary language"
    EMERGENCY_STOP = "End show immediately"
```

**Decision Logic Hierarchy:**
```
1. Emergency Checks
   ├─ Show duration reached?
   ├─ Fatal API errors?
   └─ Invalid state?

2. Segment Lifecycle
   ├─ Is current segment done?
   ├─ Should we proceed or skip next?
   └─ Time constraints?

3. Engagement Adjustments
   ├─ Energy too low/high?
   ├─ Engagement dropping?
   └─ Audience sentiment?

4. Language Switching
   ├─ High humor = code-switch?
   ├─ Emotional moment = primary language?
   └─ Smooth transitions?

5. No Change Needed
   └─ Continue current segment
```

**Example Decision Flow:**
```
remaining_time = 5 minutes
current_segment = talk_segment (10 min planned)

Decision:
- Time constraint detected
- Shorten current segment to 5 minutes
- Extend outro buffer
- Proceed as planned
```

### 2.4 LLM Generator

**Responsibilities:**
- Generate engaging radio content scripts
- Respect timing constraints from context
- Apply tone and mood instructions
- Support multilingual output
- Handle code-switching

**CRITICAL: What LLM Does NOT Do:**
- ❌ Decide when to transition segments
- ❌ Manage show timing
- ❌ Choose segment order
- ❌ Make show-level decisions

**Input Context:**
```python
class SegmentPromptContext:
    segment_type: str  # "talk_segment"
    segment_title: str  # "Today's Main Topic"
    duration_seconds: int  # 1200 = ~10 min @ 150 wpm
    language: str  # "english" or "mixed"
    mood: str  # "humorous", "serious", "informative"
    humor_level: float  # 0.0 - 1.0
    energy_level: float  # 0.0 - 1.0
    audience_size: int  # 1500
    recent_topics: List[str]  # ["weather", "news", "sports"]
    host_personality: str  # "friendly, knowledgeable"
```

**Prompt Engineering:**
```
System Prompt:
"You are a professional radio host with personality X.
Generate exactly Y words for oral delivery.
Mood is Z. Match the energy and humor levels.
Language policy: Use English for technical, Swahili for emotion.
Output raw script only - no meta-commentary."

User Prompt:
"Generate a talk segment about [topic].
Recent context: [previous segments].
Energy level: [0.0-1.0].
Connect to show theme."
```

**Output:**
```python
class SegmentScript:
    content: str  # Raw radio script
    duration_estimate: int  # ~(words * 60) / 150
    language: str
    mood: str
    metadata: dict  # token counts, generation time
```

### 2.5 TTS Engine

**Responsibilities:**
- Convert scripts to audio
- Support multiple languages/voices
- Cache frequently-used segments
- Handle ElevenLabs API

**Voice Selection:**
```python
VOICE_PROFILES = {
    "english": {
        "professional": "21m00Tcm4TlvDq8ikWAM",
        "friendly": "EXAVITQu4vr4xnSDxMaL",
        "energetic": "TM1b6xp-x50PA3kumNKl",
        "calm": "iP95p4xoKVk53GO7hXrB",
    },
    "swahili": {
        "professional": "g5CIjZEefAQXesDu2UjK",
        # ... more voices
    }
}
```

**Audio Caching:**
```
Cache Key: {segment_id}_{language}_{mood}
Storage: In-memory dict
Max Size: Unlimited (production: implement size limits)
Hit Rate: ~30% typical (repeated segments, music intros)
```

**Production Output:**
- Format: MP3 (24kHz, 128kbps)
- Streaming: Direct to audio player or S3/CDN
- Metadata: Duration, sample rate, language

### 2.6 Broadcast Loop

**Responsibilities:**
- Execute main autonomous loop
- Orchestrate all components
- Handle timing precisely
- Emit events for monitoring
- Support pause/resume

**Main Loop Pseudocode:**
```python
async def _main_loop():
    while is_running:
        # Update timing
        state.update_timing()
        
        # Check end conditions
        if state.remaining_time <= 0:
            await finish_broadcast()
            break
        
        # Get current segment
        segment = state.current_segment()
        
        # Start new segment if needed
        if not segment or segment.status == COMPLETED:
            await start_next_segment()
            continue
        
        # Get director decision
        decision = director.decide_next_action(state)
        
        # Execute decision
        await execute_director_decision(decision)
        
        # Check segment completion
        if segment_elapsed >= segment.planned_duration:
            segment.status = COMPLETED
            state.segments_completed += 1
        
        # Small sleep to prevent busy-waiting
        await asyncio.sleep(0.1)
```

**Segment Startup:**
```
1. Create SegmentExecution record
2. Emit SEGMENT_START event
3. Build LLM context from state
4. Generate script (LLM)
5. Emit CONTENT_GENERATED event
6. Synthesize audio (TTS)
7. Emit AUDIO_READY event
8. In production: Stream audio to player
9. Emit STATE_UPDATE event
```

**Event System:**
```
Events emitted:
├─ SEGMENT_START: {"segment_id", "segment_title", "duration"}
├─ CONTENT_GENERATED: {"word_count", "estimated_duration"}
├─ AUDIO_READY: {"audio_size_bytes", "duration"}
├─ DIRECTOR_DECISION: {"decision", "reason"}
├─ SEGMENT_COMPLETE: {"segment_id", "actual_duration"}
├─ STATE_UPDATE: {complete show state}
├─ ERROR: {"error_message"}
└─ BROADCAST_COMPLETE: {"segments_completed", "elapsed_time"}
```

## 3. Data Flow Diagrams

### Broadcast Startup
```
API Call: POST /api/v1/radio/shows/start
    ↓
ShowPlanner.generate_show_plan()
    ├─ Select template based on duration
    ├─ Create segments from template
    ├─ Normalize duration to fit total
    └─ Return ShowPlan (JSON-serializable)
    ↓
API Call: POST /api/v1/radio/shows/start
    ↓
RadioService.start_broadcast(show_plan)
    ├─ Create BroadcastLoop instance
    ├─ Call loop.initialize_show()
    │   ├─ Create ShowState
    │   ├─ Save to StateEngine (Redis)
    │   └─ Emit event
    └─ Call loop.start_broadcast()
        ├─ Set status = RUNNING
        ├─ Record start_time
        └─ Launch asyncio task: _main_loop()
```

### Runtime Loop
```
Main Loop Iteration (every ~100ms):
    ├─ Update state.elapsed_time
    ├─ Check if show_duration_reached()
    │   └─ Trigger: finish_broadcast() → COMPLETED
    ├─ Get current_segment
    │   └─ If none/completed: start_next_segment()
    │
    ├─ Director.decide_next_action(state)
    │   ├─ Check emergency conditions
    │   ├─ Check timing constraints
    │   ├─ Check engagement metrics
    │   └─ Return DirectorCommand
    │
    ├─ Execute DirectorCommand
    │   ├─ Adjust timing
    │   ├─ Change language
    │   ├─ Skip/extend segments
    │   └─ Update state
    │
    ├─ Check segment_elapsed >= segment.planned_duration
    │   └─ If true: Mark as COMPLETED, move to next
    │
    ├─ Save state to StateEngine
    └─ Sleep 100ms
```

### Content Generation
```
start_next_segment()
    ├─ Get next Segment from ShowPlan
    ├─ Create SegmentExecution record
    ├─ Emit: SEGMENT_START
    │
    ├─ generate_and_synthesize_segment()
    │   ├─ Simulate audience_metrics
    │   ├─ Build LLM context
    │   ├─ LLMGenerator.generate_segment_script()
    │   │   ├─ Build system prompt
    │   │   ├─ Build user prompt
    │   │   ├─ Call OpenAI API
    │   │   ├─ Parse response
    │   │   └─ Return SegmentScript
    │   ├─ Emit: CONTENT_GENERATED
    │   │
    │   ├─ TTSEngine.generate_audio()
    │   │   ├─ Check audio cache
    │   │   ├─ If not cached: Call ElevenLabs API
    │   │   ├─ Cache audio
    │   │   └─ Return AudioOutput
    │   ├─ Emit: AUDIO_READY
    │   │
    │   ├─ (Production) Stream audio to players
    │   └─ Save SegmentExecution record
    │
    └─ Save ShowState to StateEngine
```

## 4. Timing Guarantees

### Segment Timing
```
Planned Segment Duration: T_p (from ShowPlan)
Actual Segment Duration: T_a = (end_time - start_time)

Tolerance:
- Normal: T_a ≈ T_p ± 10%
- Short script: T_a may be < T_p (system waits)
- Long script: T_a may be > T_p (Director shortens)

Total Show Duration:
- Sum(T_a for all segments) = ShowPlan.total_duration ± 5%
```

### Control Points
```
1. State Update: Every 1.0s (configurable)
   └─ Check remaining time, trigger decisions

2. Segment Check: Every 0.1s (main loop)
   └─ Check if segment duration exceeded

3. Director Decision: On-demand when segment completes
   └─ Determine next action immediately

4. LLM Generation: ~2-5s (API latency)
   └─ Blocking per segment

5. TTS Synthesis: ~1-3s (API latency)
   └─ Blocking per segment
```

## 5. Scalability Considerations

### Horizontal Scaling
```
Load Balancer (API)
    ├─ Instance 1 (show_id_*_1, show_id_*_2)
    ├─ Instance 2 (show_id_*_3, show_id_*_4)
    └─ Instance N

Shared State Layer:
    ├─ Redis Cluster (state synchronization)
    └─ PostgreSQL (persistent logs)

Message Queue (optional):
    └─ RabbitMQ/Kafka for event distribution
```

### Per-Instance
```
- Max concurrent broadcasts: 5-10 (depending on API limits)
- Memory per broadcast: ~50MB (including state, cache)
- CPU per broadcast: ~0.5 cores
- Network: ~100KB/hour per broadcast
```

## 6. Error Handling & Recovery

### Failure Modes

1. **LLM API Timeout/Error**
   ```
   → Use mock script generator
   → Log error
   → Continue broadcast
   → Alert monitoring
   ```

2. **TTS API Timeout/Error**
   ```
   → Use cached audio if available
   → Use silence placeholder
   → Continue broadcast
   → Retry on next similar segment
   ```

3. **State Engine Failure (Redis)**
   ```
   → Fallback to in-memory + PostgreSQL
   → Log error
   → Attempt Redis reconnection every 30s
   → Save state to PostgreSQL every 10s
   ```

4. **Process Crash/Restart**
   ```
   → Detect unfinished shows in Redis/PostgreSQL
   → Load last known state
   → Resume from last completed segment
   → Notify users of recovery
   ```

## 7. Configuration & Deployment

### Environment Variables
```bash
# Core
ENVIRONMENT=production
DEBUG=false

# Timing
STATE_UPDATE_INTERVAL=1.0
MAX_SEGMENT_DURATION=600

# Storage
REDIS_HOST=redis.prod
REDIS_PORT=6379
DATABASE_URL=postgresql://...

# AI APIs
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...

# Features
ENABLE_PERSISTENCE=true
ENABLE_AUDIO=true
DEFAULT_LANGUAGE=english
```

### Deployment Options

**Option 1: Standalone Docker**
```bash
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  radio-ai:latest
```

**Option 2: Kubernetes**
```yaml
deployment: 3 replicas
service: load balanced
redis: stateful set
PostgreSQL: managed DB
```

**Option 3: Serverless (AWS Lambda)**
```
API Gateway → Lambda (FastAPI)
→ Lambda async workers (broadcasts)
→ DynamoDB (state)
→ S3 (audio cache)
```

## 8. Monitoring & Observability

### Metrics
```
Broadcast Metrics:
├─ Broadcasts started/completed
├─ Average broadcast duration
├─ Segments per broadcast
├─ Content generation latency
├─ TTS synthesis latency
├─ State persistence latency
└─ Error rate by component

Performance Metrics:
├─ API response times
├─ Queue depths
├─ Redis/DB query times
├─ Memory usage
└─ CPU usage per instance
```

### Logging
```
Log Levels:
├─ DEBUG: Component state transitions
├─ INFO: Segment starts, decisions, events
├─ WARNING: API delays, cache misses
├─ ERROR: Failed generations, API errors
└─ CRITICAL: System shutdown, data loss
```

## 9. Future Enhancements

1. **Real Audience Metrics**
   - Integrate with Twitter/social media sentiment
   - Real-time call-in queue
   - Listener behavior analytics

2. **Advanced Language Models**
   - Few-shot examples for consistency
   - Streaming generation (no wait time)
   - Multimodal (video + audio)

3. **Dynamic Show Adaptation**
   - Learn optimal segment lengths
   - Personalized content per listener
   - A/B testing different formats

4. **Live Intervention**
   - WebSocket for real-time control
   - Manual script injection
   - Dynamic content updates

5. **Monetization**
   - Programmatic ad insertion
   - Premium content licensing
   - Listener sponsorship integration

---

**Document Version:** 1.0
**Last Updated:** 2026-05-20
**Status:** Production Ready
