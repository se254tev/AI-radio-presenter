"""
Demonstration Script - Complete Autonomous Broadcast Example
Shows how to use the AI Radio Presenter system end-to-end
"""
import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_basic_broadcast():
    """
    Demo 1: Basic 30-minute autonomous broadcast
    Shows the minimal setup required to run a show
    """
    logger.info("=" * 60)
    logger.info("DEMO 1: Basic 30-Minute Autonomous Broadcast")
    logger.info("=" * 60)
    
    from app.services.radio_service import get_radio_service
    from app.core.broadcast_loop import BroadcastLoopEvent
    
    # Initialize service
    service = get_radio_service()
    await service.initialize({
        "openai_api_key": "mock_key",  # Use mock in demo
        "elevenlabs_api_key": "mock_key",
    })
    
    # Step 1: Create show plan
    logger.info("\n[STEP 1] Creating show plan...")
    show_plan = service.create_show_plan(
        duration_hours=0.5,  # 30 minutes
        show_name="Quick Demo Show",
        primary_language="english",
        target_audience="demo audience",
        theme="technology",
    )
    
    logger.info(f"✓ Show plan created:")
    logger.info(f"  - Show ID: {show_plan.show_id}")
    logger.info(f"  - Duration: {show_plan.total_duration}s ({show_plan.total_duration/60:.1f}min)")
    logger.info(f"  - Segments: {len(show_plan.segments)}")
    logger.info(f"  - Languages: {show_plan.primary_language}, {show_plan.secondary_language}")
    
    # Step 2: Print segments
    logger.info(f"\n[STEP 2] Show structure:")
    for i, segment in enumerate(show_plan.segments, 1):
        logger.info(f"  {i}. [{segment.segment_type.value}] {segment.title} - {segment.duration}s")
    
    # Step 3: Start broadcast with event monitoring
    logger.info(f"\n[STEP 3] Starting autonomous broadcast...")
    
    event_count = {}
    
    async def event_handler(event_type: BroadcastLoopEvent, data: dict):
        """Handle broadcast events"""
        event_name = event_type.value
        event_count[event_name] = event_count.get(event_name, 0) + 1
        
        if event_type == BroadcastLoopEvent.SEGMENT_START:
            logger.info(f"▶️  [{event_count[event_name]}] Starting: {data.get('segment_title', 'Unknown')}")
        elif event_type == BroadcastLoopEvent.CONTENT_GENERATED:
            logger.info(f"✍️  Content ready: {data.get('word_count', 0)} words")
        elif event_type == BroadcastLoopEvent.AUDIO_READY:
            logger.info(f"🔊 Audio ready: {data.get('audio_size_bytes', 0)} bytes")
        elif event_type == BroadcastLoopEvent.SEGMENT_COMPLETE:
            logger.info(f"✅ Segment complete")
        elif event_type == BroadcastLoopEvent.DIRECTOR_DECISION:
            logger.info(f"🎬 Director: {data.get('decision', 'unknown')} - {data.get('reason', '')}")
    
    broadcast = await service.start_broadcast(show_plan, event_callback=event_handler)
    
    logger.info(f"✓ Broadcast started, running autonomously...")
    
    # Step 4: Monitor in real-time
    logger.info(f"\n[STEP 4] Monitoring broadcast (real-time status):")
    
    last_segment = -1
    while True:
        status = await service.get_broadcast_status(show_plan.show_id)
        
        if status.get('status') == 'completed':
            logger.info(f"✅ Broadcast completed!")
            break
        
        # Show status update when segment changes
        current_segment = status.get('current_segment_index', -1)
        if current_segment != last_segment:
            last_segment = current_segment
            logger.info(
                f"\nStatus Update:")
                f" Time: {status['elapsed_time']}s / {status['planned_duration']}s"
                f" | Segment: {current_segment+1}/{status['total_segments']}"
                f" | Energy: {status['energy_level']:.1f}"
            )
        
        await asyncio.sleep(2)
    
    # Step 5: Print summary
    logger.info(f"\n[STEP 5] Broadcast Summary:")
    final_status = await service.get_broadcast_status(show_plan.show_id)
    logger.info(f"  - Total Time: {final_status['elapsed_time']}s")
    logger.info(f"  - Segments Completed: {final_status['segments_completed']}/{final_status['total_segments']}")
    logger.info(f"  - Final Energy Level: {final_status['energy_level']:.2f}")
    logger.info(f"  - Events Emitted: {sum(event_count.values())}")
    logger.info(f"  - Event Breakdown: {event_count}")
    
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 1 Complete!")
    logger.info("=" * 60)


async def demo_show_plan_details():
    """
    Demo 2: Detailed examination of show planning
    Shows how the Show Planner generates structure
    """
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 2: Show Plan Generation Deep Dive")
    logger.info("=" * 60)
    
    from app.core.show_planner import show_planner, SegmentType
    
    # Generate different duration shows
    durations = [3600, 7200, 10800]  # 1h, 2h, 3h
    
    for duration in durations:
        hours = duration / 3600
        logger.info(f"\n📋 Generating {hours:.0f}-hour show plan...")
        
        plan = show_planner.generate_show_plan(
            duration_seconds=duration,
            show_name=f"Demo Show ({hours:.0f}h)",
            primary_language="english",
        )
        
        # Analyze segment distribution
        segment_types = {}
        total_duration = 0
        
        for seg in plan.segments:
            seg_type = seg.segment_type.value
            segment_types[seg_type] = segment_types.get(seg_type, 0) + 1
            total_duration += seg.duration
        
        logger.info(f"  ✓ Created {len(plan.segments)} segments")
        logger.info(f"  ✓ Total duration: {total_duration}s ({total_duration/60:.1f}min)")
        logger.info(f"  ✓ Segment types:")
        for seg_type, count in sorted(segment_types.items()):
            logger.info(f"    - {seg_type}: {count}")


async def demo_director_decisions():
    """
    Demo 3: Show how the Director makes autonomous decisions
    """
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 3: Director Decision-Making")
    logger.info("=" * 60)
    
    from app.core.show_planner import show_planner, SegmentType, Mood
    from app.core.director import Director
    from app.core.state_engine import ShowState, SegmentExecution, SegmentStatus, AudienceMetrics
    from datetime import datetime, timedelta
    
    # Create a show plan
    show_plan = show_planner.generate_show_plan(
        duration_seconds=3600,
        show_name="Director Test Show",
    )
    
    # Create director
    director = Director(show_plan)
    
    # Simulate different show states
    scenarios = [
        {
            "name": "Fresh Start",
            "elapsed_time": 0,
            "remaining_time": 3600,
            "current_index": 0,
            "energy_level": 0.7,
        },
        {
            "name": "Mid-Show, Low Energy",
            "elapsed_time": 1800,
            "remaining_time": 1800,
            "current_index": 5,
            "energy_level": 0.2,
        },
        {
            "name": "Final 5 Minutes",
            "elapsed_time": 3300,
            "remaining_time": 300,
            "current_index": 10,
            "energy_level": 0.5,
        },
    ]
    
    for scenario in scenarios:
        logger.info(f"\n📊 Scenario: {scenario['name']}")
        
        # Create state
        state = ShowState(
            show_id="demo_show",
            show_name="Director Test",
            planned_duration=3600,
            elapsed_time=scenario['elapsed_time'],
            remaining_time=scenario['remaining_time'],
            current_segment_index=scenario['current_index'],
            total_segments=len(show_plan.segments),
            energy_level=scenario['energy_level'],
        )
        
        # Add some segment history
        for i in range(min(scenario['current_index'], 3)):
            seg = SegmentExecution(
                segment_id=f"seg_{i}",
                segment_type=show_plan.segments[i].segment_type.value,
                status=SegmentStatus.COMPLETED,
                planned_duration=show_plan.segments[i].duration,
            )
            state.add_segment_record(seg)
        
        # Add current segment
        current_seg_def = show_plan.segments[scenario['current_index']]
        current_seg = SegmentExecution(
            segment_id=current_seg_def.segment_id,
            segment_type=current_seg_def.segment_type.value,
            status=SegmentStatus.ACTIVE,
            planned_duration=current_seg_def.duration,
            start_time=datetime.utcnow() - timedelta(seconds=60),
        )
        state.add_segment_record(current_seg)
        state.current_segment_index = scenario['current_index']
        
        # Get director decision
        decision = director.decide_next_action(state)
        
        logger.info(f"  - Time: {scenario['elapsed_time']}s / {scenario['remaining_time']}s remaining")
        logger.info(f"  - Segment: {scenario['current_index']}")
        logger.info(f"  - Energy: {scenario['energy_level']:.1f}")
        logger.info(f"  → Decision: {decision.decision.value}")
        logger.info(f"  → Reason: {decision.reason}")
    
    logger.info(f"\n✓ Director made {len(director.decision_history)} decisions total")
    logger.info(f"✓ Decision breakdown:")
    for dec_type, count in director._count_decisions().items():
        logger.info(f"  - {dec_type}: {count}")


async def demo_state_persistence():
    """
    Demo 4: Show state persistence and recovery
    """
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 4: State Persistence & Recovery")
    logger.info("=" * 60)
    
    from app.core.state_engine import state_engine, ShowState, SegmentExecution, SegmentStatus
    from datetime import datetime
    
    logger.info("\n[Step 1] Creating and saving show state...")
    
    # Create a show state
    state = ShowState(
        show_id="persistence_demo",
        show_name="Persistence Demo Show",
        planned_duration=7200,
        elapsed_time=1200,
        remaining_time=6000,
        current_segment_index=3,
        energy_level=0.65,
    )
    
    # Add segment history
    for i in range(4):
        seg = SegmentExecution(
            segment_id=f"seg_{i}",
            segment_type="music_block" if i % 2 == 0 else "talk_segment",
            status=SegmentStatus.COMPLETED if i < 3 else SegmentStatus.ACTIVE,
            planned_duration=300,
            start_time=datetime.utcnow(),
        )
        state.add_segment_record(seg)
    
    logger.info(f"  - State created with {len(state.segment_history)} segments")
    
    # Save state
    logger.info(f"\n[Step 2] Saving state to persistence layer...")
    success = await state_engine.save_state(state)
    logger.info(f"  ✓ State saved: {success}")
    
    # Load state back
    logger.info(f"\n[Step 3] Loading state back...")
    loaded_state = await state_engine.load_state("persistence_demo")
    
    if loaded_state:
        logger.info(f"  ✓ State loaded successfully")
        logger.info(f"  - Show ID: {loaded_state.show_id}")
        logger.info(f"  - Elapsed: {loaded_state.elapsed_time}s")
        logger.info(f"  - Energy: {loaded_state.energy_level}")
        logger.info(f"  - Segments: {len(loaded_state.segment_history)}")
    else:
        logger.warning(f"  ✗ Failed to load state")
    
    logger.info(f"\n[Step 4] List active shows...")
    active_shows = await state_engine.list_active_shows()
    logger.info(f"  - Active shows: {active_shows}")


async def main():
    """Run all demos"""
    logger.info("\n🎙️  AI Radio Presenter - System Demonstrations")
    logger.info("=" * 60)
    
    # Run demos
    await demo_show_plan_details()
    await demo_director_decisions()
    await demo_state_persistence()
    
    # Run basic broadcast demo last (takes time)
    logger.info("\n⏱️  Running timed demos first, then broadcast demo...")
    await asyncio.sleep(1)
    
    try:
        await demo_basic_broadcast()
    except Exception as e:
        logger.error(f"Error in broadcast demo: {e}", exc_info=True)
    
    logger.info("\n" + "=" * 60)
    logger.info("🎙️  All demonstrations complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
