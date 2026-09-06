import os


# -------------------------------------------------
# INPUT IMAGE
# -------------------------------------------------

IMAGE_FILE = "./input/original_image.jpeg"

# -------------------------------------------------
# OUTPUT FOLDER
# -------------------------------------------------

OUTPUT_FOLDER = "./packets"

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

# -------------------------------------------------
# CHUNK SIZE
# -------------------------------------------------

CHUNK_SIZE = 128

# -------------------------------------------------
# READ IMAGE
# -------------------------------------------------

with open(IMAGE_FILE, "rb") as f:

    image_data = f.read()

# -------------------------------------------------
# SPLIT INTO CHUNKS
# -------------------------------------------------

chunks = []

for i in range(
    0,
    len(image_data),
    CHUNK_SIZE
):

    chunk = image_data[
        i:i + CHUNK_SIZE
    ]

    chunks.append(chunk)

# -------------------------------------------------
# SAVE CHUNKS
# -------------------------------------------------

for idx, chunk in enumerate(chunks):

    chunk_path = os.path.join(
        OUTPUT_FOLDER,
        f"chunk_{idx}.bin"
    )

    with open(chunk_path, "wb") as chunk_file:

        chunk_file.write(chunk)

print(
    f"\nCreated {len(chunks)} chunks"
)

print(
    f"Chunk size: {CHUNK_SIZE} bytes"
)
