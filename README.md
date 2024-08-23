# Multi-view Geometry for 3D Product Visualization in Digital Merchandising and Enhanced Customer Engagement

## Overview

This project focuses on leveraging multi-view geometry to create an advanced 3D product visualization system aimed at enhancing customer engagement in digital merchandising. By integrating state-of-the-art technologies, this system allows for immersive and interactive 3D experiences, helping customers better understand product features, which can lead to increased satisfaction and purchase likelihood.

## Features

- **Multi-view Geometry**: Enables the creation of accurate 3D models from multiple 2D images, providing a realistic view of products.
- **3D Visualization**: Uses Plotly for dynamic and interactive 3D rendering, allowing users to rotate, zoom, and inspect products in detail.
- **Depth Estimation**: Implements a deep learning-based depth estimation model to enhance the realism of 3D visualizations.
- **Convolutional Neural Networks (CNNs)**: Utilized for feature extraction from images to identify and enhance key product details.
- **GPU Acceleration**: Supports CUDA for efficient model inference and processing.

## Technologies Used

- **Python**: Core programming language.
- **Flask**: Web framework for building the user interface and handling image uploads.
- **PyTorch**: For implementing deep learning models, including CNNs for feature extraction.
- **CNN (Convolutional Neural Networks)**: Employed for image feature extraction.
- **Multi-view Geometry**: Used to reconstruct 3D models from multiple images.
- **Plotly**: Library for 3D visualization and interactive plotting.
- **Hugging Face Transformers**: For loading and running the depth estimation model.
  
## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- A CUDA-compatible GPU (optional but recommended for faster processing)

### Clone the Repository

```bash
git clone https://github.com/yourusername/3d-product-visualization.git
cd 3d-product-visualization
```


### Install Dependencies
```bash 
pip install -r requirements.txt
```

### Set Up the Flask Application

``` bash
export FLASK_APP=app.py
flask run

#or 
python app.py
```
This will start the application locally on http://127.0.0.1:5000/.

### Usage
Visit http://127.0.0.1:5000/ in your web browser.

Upload one or more images of the product from different angles.
View the generated 3D visualization and analysis.

## Model Loading and Feature Extraction
The project uses a depth estimation model from the "Depth-Anything-V2" checkpoint. The `load_model()` function loads the model and utilizes CUDA for GPU acceleration if available.

```bash
import torch
from transformers import pipeline

def load_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    checkpoint = "depth-anything/Depth-Anything-V2-base-hf"
    pipe = pipeline("depth-estimation", model=checkpoint, device=device)
    return pipe

```

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.


## License
This project is licensed under the MIT License.



