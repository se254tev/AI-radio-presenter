from typing import List, Optional
from .llm_generator import SegmentPromptContext


class PromptBuilder:
    SYSTEM_PROMPT_TEMPLATE = """You are an AI radio presenter with the following characteristics:
- Personality: {host_personality}
- Language: {language}
- Target Audience: {target_audience}
- Professionalism Level: Broadcast-quality
- Experience: 10+ years in radio

Your role is ONLY to generate compelling radio content scripts. You do NOT manage timing, segment transitions, or show structure. The show director handles all of that.

IMPORTANT CONSTRAINTS:
1. Generate exactly {words_estimate} words for this segment (allow ±10%)
2. Write for oral delivery (natural pacing, short sentences)
3. If mood is "{mood}", match that tone throughout
4. Energy level is {energy_level} (0-1 scale)
5. Humor level is {humor_level} (0-1 scale)
6. Address {audience_size} listeners

LANGUAGE POLICY:
- Primary: {language}
- Code-switching enabled: {code_switching_enabled}
{code_switching_rules}

OUTPUT FORMAT:
Only output raw script content. No meta-commentary. No markers. Just the speech.
"""

    CODE_SWITCHING_RULES = """
- Use English for: technical explanations, news delivery, clarity
- Use Swahili for: emotional moments, greetings, cultural references
- Naturally blend when appropriate (not every sentence)
- Signal transitions smoothly
- Maintain authentic voice
"""

    SEGMENT_PROMPTS = {
        "intro": """Generate an engaging radio show introduction that:
- Welcomes listeners
- Sets the energy for the show
- Hints at what's coming
- Establishes host personality
- Is warm and inviting
- Creates anticipation""",
        "music_block": """Generate engaging bridging commentary for a music block that:
- Introduces upcoming songs with brief context
- Maintains energy between tracks
- Creates smooth transitions
- Shows music knowledge
- Connects to show theme
- Keeps listeners engaged during music""",
        "talk_segment": """Generate compelling talk segment content that:
- Explores the topic thoroughly
- Maintains listener interest
- Uses concrete examples
- Invites listener participation mentally
- Balances education and entertainment
- Builds to a satisfying conclusion""",
        "news": """Generate professional news delivery that:
- Covers major current events
- Is accurate and balanced
- Uses clear, understandable language
- Contextualizes stories for listeners
- Maintains journalistic integrity
- Remains accessible to general audience""",
        "listener_interaction": """Generate engaging listener interaction that:
- Welcomes caller/listener contribution
- Shows genuine interest
- Asks follow-up questions
- Validates their perspective
- Connects to show theme
- Leaves them feeling valued""",
        "weather": """Generate engaging weather report that:
- Provides practical information
- Uses accessible language
- Connects to listener activities
- Includes personality and humor
- Gives useful forecasting
- Is entertaining, not just factual""",
        "sports_update": """Generate sports commentary that:
- Covers recent sports news
- Shows genuine enthusiasm
- Provides context for listeners
- Uses sports terminology naturally
- Connects to listener interests
- Remains entertaining""",
        "joke_break": """Generate humor content that:
- Includes clever wordplay or relatable humor
- Feels natural and not forced
- Matches show tone
- Gets listeners smiling
- Isn't offensive
- Fits the cultural context""",
        "ad_break": """Generate professional ad delivery that:
- Sounds natural and not robotic
- Highlights key benefits
- Creates curiosity
- Uses persuasive language
- Fits show tone
- Is compliant and ethical""",
        "outro": """Generate a closing segment that:
- Thanks listeners
- Recaps key moments
- Teases tomorrow's show
- Leaves positive impression
- Encourages sharing
- Says goodbye warmly""",
        "filler": """Generate filler content (music facts, trivia, quotes) that:
- Fills time naturally
- Entertains listeners
- Is interesting but not demanding
- Fits show vibe
- Can be cut short if needed
- Maintains engagement""",
    }

    @staticmethod
    def build_system_prompt(context: SegmentPromptContext) -> str:
        words_estimate = max(50, context.duration_seconds // 8)
        code_switching = ""
        if context.code_switching_enabled and context.language == "mixed":
            code_switching = PromptBuilder.CODE_SWITCHING_RULES

        return PromptBuilder.SYSTEM_PROMPT_TEMPLATE.format(
            host_personality=context.host_personality,
            language=context.language,
            target_audience=context.target_audience,
            words_estimate=words_estimate,
            mood=context.mood,
            energy_level=context.energy_level,
            humor_level=context.humor_level,
            audience_size=context.audience_size,
            code_switching_enabled=context.code_switching_enabled,
            code_switching_rules=code_switching,
        )

        @staticmethod
        def personality_summary(
                energy_level: float, mood: str, context_desc: Optional[str] = None
        ) -> str:
                """Return a short personality summary for the LLM to adopt."""
                if energy_level >= 0.75:
                        energy = "high"
                elif energy_level >= 0.4:
                        energy = "medium"
                else:
                        energy = "low"

                summary = f"Energy level: {energy} (numeric {energy_level:.2f}). Mood: {mood}."
                if context_desc:
                        summary += f" Context: {context_desc}."
                return summary

    @staticmethod
    def build_user_prompt(context: SegmentPromptContext) -> str:
        segment_instruction = PromptBuilder.SEGMENT_PROMPTS.get(
            context.segment_type,
            "Generate compelling radio content for this segment."
        )

        recent_context = ""
        if context.recent_topics:
            recent_context = f"\nRecent topics discussed: {', '.join(context.recent_topics)}"

        return f"""Segment: {context.segment_title}
Type: {context.segment_type.replace('_', ' ').title()}
Mood: {context.mood.title()}
Duration: {context.duration_seconds} seconds

{segment_instruction}

{recent_context}

Generate the radio content now:"""
