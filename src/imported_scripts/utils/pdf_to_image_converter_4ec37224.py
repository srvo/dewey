import os

from pdf2image import convert_from_path


def convert_pdf_to_images(pdf_path, output_dir) -> None:
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Convert PDF to images
    images = convert_from_path(pdf_path)

    # Save each page as an image
    for i, image in enumerate(images):
        image.save(f"{output_dir}/page_{i+1}.png", "PNG")


# PDF path and output directory
pdf_path = "/Users/srvo/ethicic.com/data/decks/NAPFA Presentation oct 3 2024 (2).pdf"
output_dir = "/Users/srvo/ethicic.com/data/decks/presentation_images"

convert_pdf_to_images(pdf_path, output_dir)
