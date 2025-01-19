from transformers import pipeline

# Load the emotion analysis model
emotion_pipeline = pipeline(
    "text-classification", model="j-hartmann/emotion-english-distilroberta-base"
)


def get_emotion(text):
    """
    Analyze emotions using j-hartmann/emotion-english-distilroberta-base.
    Returns the top emotion and its confidence score.
    """
    result = emotion_pipeline(text)
    return result[0]["label"], result[0]["score"]


# Example usage
text = "I am absolutely thrilled about this opportunity!"
emotion, confidence = get_emotion(text)
print(f"Detected Emotion: {emotion}, Confidence: {confidence:.2f}")
