import os


# -------------------------------------------------
# INPUT FOLDER
# -------------------------------------------------

INPUT_FOLDER = "./recovered_chunks"

# -------------------------------------------------
# OUTPUT IMAGE
# -------------------------------------------------

OUTPUT_IMAGE = "./reconstructed/recovered_image.jpeg"

# -------------------------------------------------
# LOAD CHUNKS
# -------------------------------------------------

chunk_files = sorted(
    [
        f for f in os.listdir(INPUT_FOLDER)
        if f.startswith("chunk_")
    ],
    key=lambda x: int(
        x.split("_")[1].split(".")[0]
    )
)

print(
    f"\nFound {len(chunk_files)} chunks"
)

# -------------------------------------------------
# REBUILD IMAGE
# -------------------------------------------------

with open(OUTPUT_IMAGE, "wb") as output_file:

    for chunk_name in chunk_files:

        path = os.path.join(
            INPUT_FOLDER,
            chunk_name
        )

        with open(path, "rb") as chunk_file:

            output_file.write(
                chunk_file.read()
            )

print(
    f"\nRecovered image saved as:"
)

print(OUTPUT_IMAGE)
