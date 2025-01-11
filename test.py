import sys
from utils import StreamInterceptor


# Example usage of the real-time output callback
def real_time_output_callback(message):
    # Write directly to the original stdout to avoid recursion
    sys.__stdout__.write(f"Captured: {message}")
    sys.__stdout__.flush()


original_stdout = sys.stdout  # Save the original stdout
stream_interceptor = StreamInterceptor(original_stdout, real_time_output_callback)

sys.stdout = stream_interceptor  # Redirect stdout to the interceptor

print(sys.stdout)
