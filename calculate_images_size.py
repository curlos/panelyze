import os

# Define the directory containing the images
directory_path = "./One Piece (Official Colored)/Ch. 567"  # Update this with the correct path to your directory


# Function to calculate total size of images
def calculate_total_image_size(directory):
    if not os.path.exists(directory):
        print("Directory does not exist.")
        return

    total_size = 0

    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)

        # Check if the file is an image
        if file_name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
            total_size += os.path.getsize(file_path)

    print(f"Total size of all images: {round(total_size / 1024, 2)} KB")


# Call the function
calculate_total_image_size(directory_path)
