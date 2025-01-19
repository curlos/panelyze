from pydub import AudioSegment


def calculate_wpm_from_audio(audio_file, text):
    """
    Calculate the Words Per Minute (WPM) rate from an audio file and text.

    :param audio_file: Path to the audio file (e.g., .wav or .mp3).
    :param text: The corresponding text for the audio file.
    :return: The calculated WPM.
    """
    # Load the audio file and get its duration in seconds
    audio = AudioSegment.from_file(audio_file)
    duration_seconds = len(audio) / 1000  # Convert milliseconds to seconds

    # Calculate the number of words in the text
    word_count = len(text.split())

    # Convert duration to minutes and calculate WPM
    duration_minutes = duration_seconds / 60
    wpm = word_count / duration_minutes if duration_minutes > 0 else 0

    return round(wpm, 2)


# Example Usage
audio_file = "output_azure.wav"  # Path to your audio file
text = "This is a test of calculating the words per minute rate from an audio file."

wpm = calculate_wpm_from_audio(audio_file, text)
print(f"Calculated WPM: {wpm}")
