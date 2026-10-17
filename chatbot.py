from config import get_model_name
from crisis import CrisisManager
from database import add_mood_log, load_chat_history as load_history_from_db, save_chat_history as save_history_to_db
from memory import MemoryManager
from screener import Screener

try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
except ModuleNotFoundError:
    nltk = None
    SentimentIntensityAnalyzer = None

try:
    from google import genai
except ModuleNotFoundError:
    genai = None


def get_missing_dependencies():
    missing = []
    if nltk is None:
        missing.append("nltk")
    if genai is None:
        missing.append("google-genai")
    return missing


def ensure_sentiment_analyzer():
    if nltk is None:
        raise RuntimeError(
            "NLTK is not installed for this Python. "
            "Install dependencies with 'python -m pip install -r requirements.txt' "
            "or run the app with the Python environment that already has them."
        )

    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        print("Downloading VADER lexicon for sentiment analysis...")
        if not nltk.download("vader_lexicon", quiet=True):
            raise RuntimeError(
                "The VADER lexicon is missing and could not be downloaded. "
                "Install it with 'python -m nltk.downloader vader_lexicon'."
            )
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError as error:
            raise RuntimeError(
                "The VADER lexicon download completed but the lexicon is still unavailable. "
                "Install it with 'python -m nltk.downloader vader_lexicon'."
            ) from error


class _GeminiTextModel:
    """Small adapter for memory extraction via the maintained GenAI SDK."""

    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    def generate_content(self, prompt):
        return self.client.models.generate_content(model=self.model_name, contents=prompt)


class Chatbot:
    """Main UDAY chatbot initialized with a user profile."""

    def __init__(self, api_key, user_email, user_profile):
        ensure_sentiment_analyzer()

        self.screener = Screener()
        self.sia = SentimentIntensityAnalyzer()
        self.user_email = user_email
        self.user_profile = user_profile

        self.history_key = user_email.lower()

        model_name = get_model_name()
        if genai is None:
            raise RuntimeError("Install the Gemini SDK with 'python -m pip install google-genai'.")
        self.client = genai.Client(api_key=api_key)
        self.base_model = _GeminiTextModel(self.client, model_name)

        self.crisis_manager = CrisisManager()
        self.memory_manager = MemoryManager(self.base_model, user_email=user_email)

        self.model_name = model_name
        self.system_instruction = self.create_system_prompt()
        past_history = self.load_chat_history()
        self.chat_session = self._new_chat(past_history, self.system_instruction)

    def _new_chat(self, history, system_instruction):
        sdk_history = []
        for message in history:
            role = message.get("role") if isinstance(message, dict) else getattr(message, "role", None)
            if role not in {"user", "model"}:
                continue
            parts = message.get("parts", []) if isinstance(message, dict) else getattr(message, "parts", [])
            text_parts = [
                {"text": part if isinstance(part, str) else part.get("text") if isinstance(part, dict) else getattr(part, "text", None)}
                for part in parts
                if (
                    isinstance(part, str)
                    or (isinstance(part, dict) and isinstance(part.get("text"), str))
                    or isinstance(getattr(part, "text", None), str)
                )
            ]
            if text_parts:
                sdk_history.append({"role": role, "parts": text_parts})
        # Bound provider context and hosted-model costs; the full transcript
        # remains available to the user through the history endpoint.
        return self.client.chats.create(
            model=self.model_name,
            history=sdk_history[-80:],
            config=genai.types.GenerateContentConfig(system_instruction=system_instruction),
        )

    def create_system_prompt(self, relevant_memories=None):
        base_prompt = """
        You are UDAY, an empathetic AI companion for mental wellness.
        Your goal is to listen, provide comfort, and suggest grounding techniques.
        CRITICAL RULES:
        1. You are NOT a doctor. Never give medical diagnoses.
        2. If a user seems stressed, suggest '5-4-3-2-1 grounding' or 'box breathing'.
        3. Be warm, human-like, and concise.
        4. Encourage professional support for serious or persistent distress.
        """

        memories = "\n".join(f"- {fact}" for fact in (relevant_memories or []))
        return (
            base_prompt
            + "\n\nUSER CONTEXT:\n"
            + "Only use the explicitly reviewed memories below. Do not infer sensitive traits.\n"
            + f"\nLONG TERM MEMORIES (Past chats):\n{memories}\n"
            + "\nINSTRUCTION: Use the context above to personalize your advice."
        )

    def load_chat_history(self):
        history = load_history_from_db(self.history_key)
        return history if isinstance(history, list) else []

    def save_chat_history(self):
        history_data = []
        for message in self.chat_session.get_history():
            history_data.append(
                {"role": message.role, "parts": [part.text for part in message.parts]}
            )
        save_history_to_db(self.history_key, history_data)

    def log_mood(self, score, text_preview):
        # Store the score only; raw message excerpts are sensitive and unnecessary.
        add_mood_log(self.history_key, score, "")

    def save_long_term_memory(self):
        recent_text = ""
        for message in self.chat_session.get_history()[-10:]:
            role = "User" if message.role == "user" else "UDAY"
            recent_text += f"{role}: {message.parts[0].text}\n"

        if recent_text:
            self.memory_manager.update_memory(recent_text)

    def analyze_and_adjust_prompt(self, user_text):
        scores = self.sia.polarity_scores(user_text)
        compound_score = scores["compound"]
        self.log_mood(compound_score, user_text)

        if compound_score < -0.4:
            return user_text + " [SYSTEM ALERT: User sentiment is very negative. Be extra validating.]"
        return user_text

    def get_response(self, user_input):
        if self.screener.is_active:
            return self.screener.process_input(user_input)

        if "screening" in user_input.lower():
            return self.screener.start_screening()

        try:
            final_prompt = self.analyze_and_adjust_prompt(user_input)
            relevant_memories = self.memory_manager.get_relevant_facts(user_input)
            system_instruction = self.create_system_prompt(relevant_memories)
            self.chat_session = self._new_chat(self.chat_session.get_history(), system_instruction)
            response = self.chat_session.send_message(message=final_prompt)
            self.save_chat_history()
            return response.text
        except Exception as error:
            # Do not persist or log user text or provider payloads.
            raise RuntimeError("The AI service is temporarily unavailable. Please try again shortly.") from error
