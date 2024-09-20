import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import os

def process_and_save_csv(input_csv_path, output_csv_path, max_products=None):
    # Read the CSV file
    df = pd.read_csv(input_csv_path)
    
    # Extract product_id from meta
    df['product_id'] = df['meta'].str.split(':').str[0]
    
    # Create is_main column
    df['is_main'] = df['meta'].str.endswith(':main')
    
    # Add full path to images
    df['full_path'] = "../data/small/" + df['path']
    
    # Group by product_id and aggregate
    grouped = df.groupby('product_id').agg({
        'full_path': lambda x: '|'.join(x),
        'is_main': lambda x: '|'.join(x.astype(str))
    }).reset_index()
    
    # Separate main image and other images
    def split_images(row):
        paths = row['full_path'].split('|')
        is_mains = row['is_main'].split('|')
        main_image = next((path for path, is_main in zip(paths, is_mains) if is_main == 'True'), None)
        other_images = [path for path, is_main in zip(paths, is_mains) if is_main == 'False']
        return pd.Series({'main_image': main_image, 'other_images': '|'.join(other_images)})

    grouped[['main_image', 'other_images']] = grouped.apply(split_images, axis=1)
    
    # Drop unnecessary columns
    grouped = grouped.drop(columns=['full_path', 'is_main'])
    
    if max_products:
        grouped = grouped.head(max_products)
    
    # Save to CSV
    grouped.to_csv(output_csv_path, index=False)
    
    return grouped

def load_processed_csv(csv_path):
    df = pd.read_csv(csv_path)
    df['other_images'] = df['other_images'].apply(lambda x: x.split('|') if pd.notna(x) else [])
    return df

# Main execution
input_csv_path = '../data/metadata/abo-mvr.csv'  # Replace with your actual input CSV file path
processed_csv_path = './metadata.csv'  # Replace with desired output CSV file path
max_products = None  # Set to a number if you want to limit the products processed

# Check if processed CSV exists
if os.path.exists(processed_csv_path):
    print("Loading pre-processed data...")
    dataset = load_processed_csv(processed_csv_path)
else:
    print("Processing and saving data...")
    dataset = process_and_save_csv(input_csv_path, processed_csv_path, max_products)
