EMOTION_MODEL_NAME = "j-hartmann/emotion-english-distilroberta-base"

# For each emotion the model can find, the Azure voice styles that fit it, best first. Not every Azure voice has every style, so the first one the voice actually has is used.
AZURE_STYLES_BY_EMOTION = {
    "anger": ["angry", "shouting", "disgruntled", "unfriendly", "envious"],
    "disgust": ["disgruntled", "unfriendly", "embarrassed", "envious"],
    "fear": ["terrified", "fearful", "shouting", "sorry", "shy", "whispering", "envious"],
    "joy": [
        "cheerful",
        "excited",
        "affectionate",
        "gentle",
        "friendly",
        "relieved",
        "hopeful",
        "empathetic",
        "sports-commentary-excited",
        "lyrical",
    ],
    "neutral": [
        "calm",
        "serious",
        "chat",
        "newscast",
        "assistant",
        "customerservice",
        "narration-professional",
        "newscast-casual",
        "newscast-formal",
        "conversation",
        "poetry-reading",
        "chat-casual",
        "narration-relaxed",
        "sports-commentary",
        "documentary-narration",
        "livecommercial",
        "story",
        "advertisement-upbeat",
    ],
    "sadness": ["depressed", "sad", "sorry", "shy"],
    "surprise": ["excited", "embarrassed", "sports-commentary-excited"],
}


# How sure the model has to be before a line gets a voice style. Plain, emotionless sentences often get a low-confidence guess (e.g. "The meeting starts at noon." was 43% "fear"), and those are better read in the normal voice.
MIN_EMOTION_CONFIDENCE = 0.5


class EmotionAnalyzer:
    """
    Finds the emotion of a line of text (anger, joy, sadness, etc.) so Azure Text-To-Speech can read it in a matching voice style. Only used with Azure's "Auto (emotion of each line)" voice style.

    The emotion model (about 330 MB) is only loaded the first time it's needed. The first time ever, it's downloaded from Hugging Face automatically.
    """

    def __init__(self):
        self._emotion_pipeline = None

    @property
    def emotion_pipeline(self):
        if self._emotion_pipeline is None:
            # Imported here so that transformers only loads when emotions are actually used.
            from transformers import pipeline

            print(
                "Loading the emotion model (the first time, this downloads about 330 MB)..."
            )
            self._emotion_pipeline = pipeline("text-classification", model=EMOTION_MODEL_NAME)

        return self._emotion_pipeline

    def get_emotion(self, text):
        """
        The text's strongest emotion and how sure the model is (0 to 1).
        """
        # The model only reads about 512 words at a time. Longer text is cut off instead of raising an error.
        result = self.emotion_pipeline(text, truncation=True)
        return result[0]["label"], result[0]["score"]

    def get_voice_style(self, text, voice_styles):
        """
        The best Azure voice style for the text's emotion that the voice has (one of "voice_styles"), or "" (the normal voice) if none fits or the model isn't sure about the emotion.
        """
        emotion, confidence = self.get_emotion(text)

        if confidence < MIN_EMOTION_CONFIDENCE:
            return ""

        for style in AZURE_STYLES_BY_EMOTION.get(emotion, []):
            if style in voice_styles:
                return style

        return ""


_shared_emotion_analyzer = None


def get_emotion_analyzer():
    """
    The one EmotionAnalyzer the app shares, so its model is only loaded once.
    """
    global _shared_emotion_analyzer

    if _shared_emotion_analyzer is None:
        _shared_emotion_analyzer = EmotionAnalyzer()

    return _shared_emotion_analyzer
