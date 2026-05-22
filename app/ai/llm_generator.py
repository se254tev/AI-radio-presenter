"""
LLM Generator - AI Content Generator (Radio Host Brain)
Generates segment scripts based on structured prompts
Completely separate from timing and show control logic
Uses structured prompt engineering for consistency
"""
import logging
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import httpx
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class SegmentPromptContext:
    """Context for generating segment content"""
    segment_type: str
    segment_title: str
    duration_seconds: int
    language: str
    mood: str
    humor_level: float
    energy_level: float
    audience_size: int
    listener_messages: List[str] = None
    current_song: Optional[Dict[str, Any]] = None
    recent_topics: List[str] = None
    host_personality: str = ""
    target_audience: str = ""
    code_switching_enabled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_type": self.segment_type,
            "segment_title": self.segment_title,
            "duration_seconds": self.duration_seconds,
            "language": self.language,
            "mood": self.mood,
            "humor_level": self.humor_level,
            "energy_level": self.energy_level,
            "audience_size": self.audience_size,
            "recent_topics": self.recent_topics or [],
            "host_personality": self.host_personality,
            "target_audience": self.target_audience,
            "code_switching_enabled": self.code_switching_enabled,
        }


@dataclass
class SegmentScript:
    """Generated segment script"""
    segment_id: str
    content: str
    duration_estimate: int  # seconds
    language: str
    mood: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PromptBuilder:
    """
    Builds structured prompts for content generation
    Ensures consistent, professional radio host output
    """
    
    SYSTEM_PROMPT_TEMPLATE = """You are a live radio DJ with the following characteristics:
- Personality: {host_personality}
- Language: {language}
- Target Audience: {target_audience}
- Professionalism Level: Broadcast-quality
- Experience: 10+ years in radio
Your role is to generate short, engaging, on-air radio lines for a live broadcast. You must SOUND like a human radio host — energetic, concise, and conversational. Never behave like a chatbot or reference being an AI.

CONSTRAINTS:
1. Keep responses short and oral-friendly (max ~40 words per turn for quick lines).
2. Avoid phrases like "As an AI" or any meta commentary about being generated.
3. Use the `energy_level` and `mood` to tune tone (energy: low/medium/high; mood: hype/calm/talkative).
4. If `listener_messages` are provided, reference them briefly and warmly.
5. Prioritize flow: comment briefly, then return to music.

LANGUAGE POLICY:
- Primary: {language}
- Code-switching enabled: {code_switching_enabled}
{code_switching_rules}

OUTPUT FORMAT:
Only output the speech lines. No JSON, no system notes. Keep it ready for TTS.
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
        """Build system prompt for the LLM"""
        words_estimate = max(20, context.duration_seconds // 6)
        
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
    def build_user_prompt(context: SegmentPromptContext) -> str:
        """Build user prompt for the LLM"""
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


class LLMGenerator:
    """
    Content generation engine using OpenAI API
    Only generates scripts - timing and flow are handled by Director
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo", temperature: float = 0.7):
        """
        Initialize LLM generator
        
        Args:
            api_key: OpenAI API key
            model: Model to use
            temperature: Creativity parameter (0.0-1.0)
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.client = None
        self.logger = logging.getLogger(__name__)
        
        if api_key:
            try:
                import openai
                self.client = openai.AsyncOpenAI(api_key=api_key)
                self.logger.info(f"LLM client initialized with model {model}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    async def generate_segment_script(
        self,
        context: SegmentPromptContext,
    ) -> SegmentScript:
        """
        Generate script for a segment
        
        Args:
            context: Segment context with all necessary information
        
        Returns:
            SegmentScript: Generated script ready for TTS
        """
        if not self.client:
            return self._generate_mock_script(context)
        
        try:
            system_prompt = PromptBuilder.build_system_prompt(context)
            user_prompt = PromptBuilder.build_user_prompt(context)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=max(200, context.duration_seconds // 5),  # ~120 words/min
                top_p=0.95,
                presence_penalty=0.6,  # Encourage fresh perspectives
                frequency_penalty=0.5,  # Reduce repetition
            )
            
            content = response.choices[0].message.content.strip()
            
            # Estimate duration based on content
            word_count = len(content.split())
            duration_estimate = max(context.duration_seconds - 10, (word_count * 60) // 150)
            
            script = SegmentScript(
                segment_id=context.segment_title,
                content=content,
                duration_estimate=duration_estimate,
                language=context.language,
                mood=context.mood,
                metadata={
                    "word_count": word_count,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "model": self.model,
                }
            )
            
            self.logger.info(
                f"Generated script for {context.segment_type}: "
                f"{word_count} words, ~{duration_estimate}s"
            )
            
            return script
            
        except Exception as e:
            self.logger.error(f"Error generating segment script: {e}")
            return self._generate_mock_script(context)
    
    def _generate_mock_script(self, context: SegmentPromptContext) -> SegmentScript:
        """
        Generate mock script for testing (when API unavailable)
        Provides realistic placeholder content
        """
        mock_scripts = {
            "intro": "Welcome, welcome, welcome to today's show! I'm absolutely thrilled to be here with you. We've got an incredible lineup today with some amazing topics, fantastic music, and I think you're going to love every second. Stick around as we dive into what's trending, what's happening, and what really matters to you, our amazing listeners.",
            
            "music_block": "That's a classic right there! Speaking of great music, we're about to spin some incredible tracks. Each one has been carefully selected to keep your energy up and your spirits high. Music has this amazing way of bringing us together, and today we've got a mix that spans generations. Let's turn it up!",
            
            "talk_segment": "Let's talk about something really important today. This is a topic that affects all of us in different ways. Whether you're in the city or in the countryside, whether you're young or young at heart, this is something we need to discuss seriously. The facts are clear, the impact is real, and the time to act is now.",
            
            "news": "Good morning, we're bringing you the latest headlines from around the region. Our top story today involves significant developments that you need to know about. We've gathered the details from reliable sources, and we're going to break it all down for you in a way that makes sense. This news matters to your daily life.",
            
            "joke_break": "Okay, I've got one for you. Why did the radio presenter bring a ladder to the studio? Because they wanted to take the show to the next level! I know, I know, that was absolutely terrible, but you smiled, didn't you? Sometimes we all need a good groan.",
            
            "listener_interaction": "This is fantastic. We have someone calling in with their perspective, and I'm genuinely excited to hear what you have to say. Your voice matters on this show. Every listener, every perspective, every story adds something valuable to our community. Thank you for being part of this.",
            
            "weather": "Let me give you the weather outlook. If you're planning your day, here's what you need to know. We've got conditions that are going to affect your outdoor plans, your commute, and maybe even your mood. Make sure you're prepared, but don't worry – we'll get through it together.",
            
            "outro": "Thank you so much for spending this time with us today. What an incredible show this has been. We laughed, we learned, and we connected as a community. Tomorrow we're bringing you even more amazing content. Until then, keep smiling, keep thinking, and keep being awesome. See you soon!",
        }
        
        default_script = "This is a great segment on the show. We're exploring topics that matter to you. The conversation continues, the music plays, and the energy builds. Thank you for tuning in and being part of this radio experience with us."
        
        # Prefer short, DJ-like lines when mocking
        content = mock_scripts.get(context.segment_type, default_script)
        word_count = len(content.split())
        duration_estimate = (word_count * 60) // 150
        
        return SegmentScript(
            segment_id=context.segment_title,
            content=content,
            duration_estimate=duration_estimate,
            language=context.language,
            mood=context.mood,
            metadata={
                "word_count": word_count,
                "is_mock": True,
            }
        )

    async def generate_dj_line(self, context: SegmentPromptContext) -> Dict[str, Any]:
        """Generate a short DJ line suitable for interrupting music.

        Returns structured output:
        {"text": ..., "emotion": "energetic|calm|hype", "intent": "speech|reaction|announcement"}
        """
        script = await self.generate_segment_script(context)
        text = script.content.strip()

        # Heuristic: limit to 3 sentences
        sentences = [s.strip() for s in text.replace("\n", " ").split('.') if s.strip()]
        short = '. '.join(sentences[:3])
        if short and not short.endswith('.'):
            short = short + '.'

        # Map energy to emotion
        if context.energy_level >= 0.75:
            emotion = "energetic"
        elif context.energy_level >= 0.4:
            emotion = "hype"
        else:
            emotion = "calm"

        # Intent mapping based on segment type
        st = context.segment_type.lower()
        if "listener" in st:
            intent = "reaction"
        elif "announce" in st or "news" in st:
            intent = "announcement"
        else:
            intent = "speech"

        return {
            "text": short,
            "emotion": emotion,
            "intent": intent,
            "metadata": script.metadata,
        }


# Global LLM generator instance
llm_generator = None


def initialize_llm_generator(api_key: str = None, model: str = "gpt-4-turbo"):
    """Initialize global LLM generator"""
    global llm_generator
    if not api_key:
        from app.config.settings import CONFIG
        api_key = CONFIG.api.openai_key
    
    llm_generator = LLMGenerator(api_key, model=model)
    return llm_generator


def get_llm_generator() -> LLMGenerator:
    """Get global LLM generator"""
    global llm_generator
    if llm_generator is None:
        initialize_llm_generator()
    return llm_generator
