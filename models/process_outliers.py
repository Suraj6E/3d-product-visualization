from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KDTree
import plotly.graph_objects as go
import numpy as np

def remove_outliers(fig, spatial_strictness=1.0, color_threshold=0.05, min_cluster_size=5):
    """
    Removes outliers from a 3D point cloud based on both spatial distribution and color.
    
    Parameters:
    -----------
    fig : plotly.graph_objects.Figure
        Input figure containing the 3D scatter plot
    spatial_strictness : float, default=1.0
        Controls how strict the spatial clustering should be:
        - Lower values (e.g., 0.5) are more lenient and keep more points
        - Higher values (e.g., 2.0) are stricter and remove more points
        - 1.0 is the default balanced setting
    color_threshold : float, default=0.05
        The minimum percentage (0.0 to 1.0) of points a color cluster needs to be considered valid
    min_cluster_size : int, default=5
        Minimum number of points needed to form a valid cluster
    
    Returns:
    --------
    plotly.graph_objects.Figure
        New figure with outliers removed
    """
    def calculate_dynamic_dbscan_params(points, strictness):
        # Create KD-tree for efficient nearest neighbor search
        point_tree = KDTree(points)
        # Get distances to k nearest neighbors
        distances, _ = point_tree.query(points, k=6)  # k=6 gives 5 neighbors + self
        
        # Calculate average distance to nearest neighbors
        avg_distance = np.mean(distances[:, 1:])  # Exclude distance to self
        
        # Adjust eps based on strictness parameter
        # Lower strictness = larger eps = more lenient clustering
        eps = avg_distance * (2.0 / strictness)
        
        # Calculate dynamic minimum samples
        # Base number is min_cluster_size, scaled by log of point count
        point_count_factor = np.log10(len(points)) / 4  # Divide by 4 to make it less strict
        min_samples = max(min_cluster_size, int(point_count_factor * min_cluster_size))
        
        return eps, min_samples

    def analyze_color_clusters(colors, threshold):
        """
        Analyzes color distribution using color distance and density-based grouping.
        
        Parameters:
        -----------
        colors : numpy.ndarray
            Array of RGB colors
        threshold : float
            Threshold for considering a color group significant (0.0 to 1.0)
        
        Returns:
        --------
        numpy.ndarray
            Boolean mask of valid colors
        """
        def color_distance(c1, c2):
            """
            Calculates a weighted color distance that's more perceptually accurate.
            Gives more weight to differences in the same color channel.
            """
            # Convert to float to avoid overflow
            c1 = c1.astype(float)
            c2 = c2.astype(float)
            
            # Calculate channel differences
            dr = c1[0] - c2[0]
            dg = c1[1] - c2[1]
            db = c1[2] - c2[2]
            
            # Weight the differences (giving more weight to same-channel differences)
            return np.sqrt(2*dr*dr + 4*dg*dg + 3*db*db)

        # Find the dominant color (the color that appears most frequently)
        unique_colors, color_counts = np.unique(colors, axis=0, return_counts=True)
        dominant_color = unique_colors[np.argmax(color_counts)]
        
        # Calculate distances from each point to the dominant color
        distances = np.array([color_distance(color, dominant_color) for color in colors])
        
        # Calculate adaptive threshold based on the distribution of distances
        distance_threshold = np.percentile(distances, threshold * 100)
        
        # Create mask for colors within threshold
        valid_colors = distances <= distance_threshold
        
        return valid_colors

    # Extract points and colors from figure
    trace = fig.data[0]
    points = np.column_stack([trace.x, trace.y, trace.z])
    colors = np.array([list(map(int, c.strip('rgb()').split(','))) 
                      for c in trace.marker.color])
    
    # Scale the points
    scaler = StandardScaler()
    xy_scaled = scaler.fit_transform(points[:, :2])
    z_scaled = scaler.fit_transform(points[:, 2:3]) * 2  # Weight depth more
    points_scaled = np.column_stack([xy_scaled, z_scaled])
    
    # Get dynamic parameters and perform spatial clustering
    eps, min_samples = calculate_dynamic_dbscan_params(points_scaled, spatial_strictness)
    spatial_clusters = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        n_jobs=-1
    ).fit_predict(points_scaled)
    
    # Get valid points from spatial clustering
    valid_spatial = spatial_clusters != -1
    
    # Get valid points from color analysis
    valid_colors = analyze_color_clusters(colors, color_threshold)
    
    # Combine both masks
    valid_points = valid_spatial & valid_colors
    
    # Print final statistics
    total_points = len(points)
    kept_points = np.sum(valid_points)
    
    print(f"Outliers removed: {total_points - kept_points}")
    
    # Create new figure with cleaned points
    cleaned_fig = go.Figure(data=[go.Scatter3d(
        x=points[valid_points, 0],
        y=points[valid_points, 1],
        z=points[valid_points, 2],
        mode='markers',
        marker=dict(
            size=trace.marker.size,
            color=[f'rgb({r},{g},{b})' for r,g,b in colors[valid_points]],
            opacity=trace.marker.opacity
        )
    )])
    
    # Copy layout from original figure
    cleaned_fig.update_layout(fig.layout)
    
    return cleaned_fig