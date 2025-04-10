import os
import argparse
import glob
from test_app import ocr_with_surya, save_results_to_word, save_results_to_file, draw_boxes_on_image

def process_directory(directory_path, languages, output_folder=None, file_types=None):
    """
    Process all images in a directory with OCR.
    
    Args:
        directory_path (str): Path to the directory containing images
        languages (str): Comma-separated list of language codes
        output_folder (str, optional): Folder to save results. Defaults to None (same as input).
        file_types (list, optional): List of file extensions to process. Defaults to ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'].
    """
    if file_types is None:
        file_types = ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']
    
    if output_folder is None:
        output_folder = directory_path
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Find all image files
    image_files = []
    for file_type in file_types:
        pattern = os.path.join(directory_path, f'*{file_type}')
        image_files.extend(glob.glob(pattern))
        pattern = os.path.join(directory_path, f'*{file_type.upper()}')
        image_files.extend(glob.glob(pattern))
    
    print(f"Found {len(image_files)} image(s) to process")
    
    # Process each image
    for i, image_path in enumerate(image_files):
        print(f"\nProcessing image {i+1}/{len(image_files)}: {image_path}")
        
        # Get base file name
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # Set output paths
        output_text = os.path.join(output_folder, f"{base_name}_ocr.txt")
        output_word = os.path.join(output_folder, f"{base_name}_ocr.docx")
        output_image = os.path.join(output_folder, f"{base_name}_boxes.jpg")
        
        # Process the image
        results = ocr_with_surya(image_path, languages)
        
        if "error" in results:
            print(f"Error processing {image_path}: {results['error']}")
            continue
        
        # Save results
        save_results_to_file(results, output_text)
        save_results_to_word(results, output_word)
        draw_boxes_on_image(image_path, results, output_image)
    
    print(f"\nProcessing complete. Results saved to {output_folder}")

def main():
    parser = argparse.ArgumentParser(description="Batch OCR Processing")
    parser.add_argument("directory", help="Directory containing images to process")
    parser.add_argument("--langs", default="tr,en", help="Languages (comma-separated, default: tr,en)")
    parser.add_argument("--output", help="Output directory (default: same as input)")
    parser.add_argument("--types", help="File types to process (comma-separated, default: jpg,jpeg,png,tif,tiff,bmp)")
    
    args = parser.parse_args()
    
    # Process file types if specified
    file_types = None
    if args.types:
        file_types = [f".{ext.lower()}" for ext in args.types.split(',')]
    
    process_directory(args.directory, args.langs, args.output, file_types)

if __name__ == "__main__":
    main() 