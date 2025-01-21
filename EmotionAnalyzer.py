from pprint import pprint
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

    def get_emotions_from_text_matrix(self, text_matrix):
        text_obj_matrix = []

        for text_arr in text_matrix:
            new_text_obj_arr = []

            for text in text_arr:
                result = self.get_emotion(text)
                emotion, confidence = result

                new_text_obj_arr.append(
                    {"text": text, "emotion": emotion, "confidence": confidence}
                )

            text_obj_matrix.append(new_text_obj_arr)

        return text_obj_matrix


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    emotion_analyzer = EmotionAnalyzer()

    essential_text_in_images_matrix = [
        [
            "Red Line: Holy Land of Mariejoa",
            "vanished...?",
            "Yeah. That's what happened.",
            "I don't mean just like a figure of speech, either. He literally vanished into thin air!!",
            "Fuffuffu... it sure took me by surprise, I'll tell you that. Does the Kage Kage no mi have that kind of power?",
            "This is no joking matter!!!",
        ],
        [
            "Ahh, don't worry... He was half-dead already. There was no saving him, no matter where he went.",
            "Well... unless he managed to resurrect himself as a zombie, of course... Fuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffu! Hey, it serves him right.",
            "And you call this doing your job, do you...?!!!",
        ],
    ]

    result = emotion_analyzer.get_emotions_from_text_matrix(
        essential_text_in_images_matrix
    )
    pprint(result)
