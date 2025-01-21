# app/routes/visualization.py
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
import time
import json

visualization = Blueprint('visualization', __name__)

@visualization.route('/process/<folder_name>')
@login_required
def process_folder(folder_name):
    """Process images with enhanced monitoring and quality analysis"""
    try:
        # Get file paths
        folder_path = current_app.config['UPLOAD_FOLDER'] / folder_name
        views = {
            'front': next(folder_path.glob('front.*'), None),
            'back': next(folder_path.glob('back.*'), None),
            'top': next(folder_path.glob('top.*'), None)
        }
        
        # Validate files exist
        if not all(views.values()):
            return jsonify({
                'success': False,
                'message': 'Missing required view files'
            })

        # Process with enhanced visualization system
        result = current_app.visualizer.process_orthogonal_views(
            str(views['front']),
            str(views['back']),
            str(views['top']),
            depth_threshold=current_app.config['MODEL_SETTINGS']['depth_threshold'],
            sampling_rate=current_app.config['MODEL_SETTINGS']['sampling_rate']
        )
        
        # Save results
        plot_file = folder_path / 'plot_data.json'
        with open(plot_file, 'w') as f:
            json.dump(result['visualization'], f)
            
        # Return success with metrics
        return jsonify({
            'success': True,
            'plot': result['visualization'],
            'metrics': result['metrics'],
            'quality': result['quality_summary']
        })
        
    except Exception as e:
        current_app.logger.error(f"Processing error: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })