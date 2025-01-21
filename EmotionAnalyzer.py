from transformers import pipeline


class EmotionAnalyzer:
    def __init__(self):
        # Load the emotion analysis model
        self.emotion_pipeline = pipeline(
            "text-classification", model="j-hartmann/emotion-english-distilroberta-base"
        )

    def get_emotion(self, text):
        """
        Analyze emotions using j-hartmann/emotion-english-distilroberta-base.
        Returns the top emotion and its confidence score.
        """
        result = self.emotion_pipeline(text)
        return result[0]["label"], result[0]["score"]


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    emotion_analyzer = EmotionAnalyzer()

    # Example usage
    text = "I am absolutely thrilled about this opportunity!"
    emotion, confidence = emotion_analyzer.get_emotion(text)
    print(f"Detected Emotion: {emotion}, Confidence: {confidence:.2f}")
