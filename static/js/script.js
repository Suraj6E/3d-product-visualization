document.addEventListener('DOMContentLoaded', (event) => {
    const fileInput = document.getElementById('file-input');
    const folderTitle = document.getElementById('folder-title');
    const preview = document.getElementById('preview');
    const gallery = document.getElementById('gallery');
    const foldersList = document.getElementById('folders-list');
    const saveFolderBtn = document.getElementById('save-folder');
    const folderSaveArea = document.getElementById('folder-save-area');
    const processingStatus = document.getElementById('processing-status');
    const plotContainer = document.getElementById('plot-container');

    // Add feedback submission handler
    const submitFeedbackBtn = document.getElementById('submit-feedback');
    if (submitFeedbackBtn) {
        submitFeedbackBtn.addEventListener('click', submitFeedback);
    }
    
    // Add rating button handlers
    document.querySelectorAll('.rating-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.rating-btn').forEach(b => 
                b.classList.remove('selected'));
            e.target.classList.add('selected');
        });
    });

    let selectedFiles = [];
    let currentFolder = null;

    const socket = io();
    
    socket.on('processing_status', function(data) {
        if (data.status === 'started') {
            processingStatus.innerHTML = `Processing images in folder "${data.folder}"...`;
        } else if (data.status === 'failed') {
            processingStatus.innerHTML = `Failed to process images in folder "${data.folder}"`;
        }
    });

    socket.on('processing_result', function(data) {
        processingStatus.innerHTML = `Finished processing images in folder "${data.folder}"`;
        Plotly.newPlot(plotContainer, JSON.parse(data.plot));
    });

    fileInput.addEventListener('change', function(e) {
        const newFiles = Array.from(this.files);
        selectedFiles = [...selectedFiles, ...newFiles];
        updatePreview();
        folderSaveArea.style.display = 'block';
        if (currentFolder) {
            folderTitle.value = currentFolder;
            saveFolderBtn.textContent = 'Add Images to Folder';
        } else {
            saveFolderBtn.textContent = 'Save Images to New Folder';
        }
    });

    saveFolderBtn.addEventListener('click', function() {
        if (selectedFiles.length > 0 && folderTitle.value) {
            uploadFiles(selectedFiles, folderTitle.value);
        } else {
            alert('Please select files and enter a folder title before saving.');
        }
    });

    foldersList.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-folder')) {
            e.stopPropagation();
            const folderName = e.target.dataset.folder;
            deleteFolder(folderName);
        } else {
            const folderElement = e.target.closest('.folder');
            if (folderElement) {
                const folderName = folderElement.dataset.folder;
                setActiveFolder(folderElement);
                displayFolderImages(folderName);
                processFolder(folderName);
            }
        }
    });

    function setActiveFolder(folderElement) {
        document.querySelectorAll('.folder').forEach(f => f.classList.remove('active'));
        folderElement.classList.add('active');
        currentFolder = folderElement.dataset.folder;
        folderTitle.value = currentFolder;
        saveFolderBtn.textContent = 'Add Images to Folder';
    }

    function updatePreview() {
        preview.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const container = document.createElement('div');
            container.className = 'preview-image-container';

            const img = document.createElement('img');
            img.className = 'preview-image';
            img.file = file;

            const removeBtn = document.createElement('button');
            removeBtn.className = 'remove-image';
            removeBtn.innerHTML = 'X';
            removeBtn.addEventListener('click', () => removeImage(index));

            container.appendChild(img);
            container.appendChild(removeBtn);
            preview.appendChild(container);

            const reader = new FileReader();
            reader.onload = (function(aImg) { return function(e) { aImg.src = e.target.result; }; })(img);
            reader.readAsDataURL(file);
        });
    }

    function removeImage(index) {
        selectedFiles.splice(index, 1);
        updatePreview();
        if (selectedFiles.length === 0) {
            folderSaveArea.style.display = 'none';
        }
    }

    function uploadFiles(files, folderTitle) {
        const formData = new FormData();
        formData.append('folder_title', folderTitle);
        files.forEach(file => {
            formData.append('files[]', file);
        });

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Files uploaded successfully');
                location.reload();
            } else {
                alert('Error uploading files');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred during the upload');
        });
    }

    // function displayFolderImages(folderName) {
    //     gallery.innerHTML = '';
    //     fetch(`/get_images/${folderName}`)
    //         .then(response => response.json())
    //         .then(data => {
    //             if (data.success) {
    //                 data.images.forEach(image => {
    //                     const imgContainer = document.createElement('div');
    //                     imgContainer.className = 'preview-image-container';
    
    //                     const img = document.createElement('img');
    //                     img.src = `/get_image/${folderName}/${image}`;
    //                     img.alt = image;
    //                     img.className = 'preview-image';
    
    //                     // Add click handler for showing feedback section
    //                     imgContainer.addEventListener('click', () => {
    //                         showFeedbackSection(folderName, image);
    //                     });
    
    //                     const deleteBtn = document.createElement('button');
    //                     deleteBtn.className = 'remove-image';
    //                     deleteBtn.textContent = '×';
    //                     deleteBtn.onclick = (e) => {
    //                         e.stopPropagation(); // Prevent triggering the container's click
    //                         deleteImage(folderName, image);
    //                     };
    
    //                     imgContainer.appendChild(img);
    //                     imgContainer.appendChild(deleteBtn);
    //                     gallery.appendChild(imgContainer);
    //                 });
    //             } else {
    //                 console.error('Error:', data.message);
    //             }
    //         })
    //         .catch(error => console.error('Error:', error));
    // }

    function deleteImage(folderName, imageName) {
        if (confirm(`Are you sure you want to delete ${imageName}?`)) {
            fetch(`/delete_image/${folderName}/${imageName}`, { method: 'DELETE' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        displayFolderImages(folderName);
                    } else {
                        alert('Error deleting image');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while deleting the image');
                });
        }
    }

    function deleteFolder(folderName) {
        if (confirm(`Are you sure you want to delete the folder "${folderName}" and all its contents?`)) {
            fetch(`/delete_folder/${folderName}`, { method: 'DELETE' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload(); // Refresh the page to update the folder list
                    } else {
                        alert('Error deleting folder');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while deleting the folder');
                });
        }
    }

    function processFolder(folderName) {
        fetch(`/process_image/${folderName}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log(data.message);
                } else {
                    console.error(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while processing the folder');
            });
    }

    function setupFeedbackSystem() {
        const feedbackSection = document.getElementById('feedback-section');
        const ratingBtns = document.querySelectorAll('.rating-btn');
        const submitBtn = document.getElementById('submit-feedback');
        const commentInput = document.getElementById('feedback-comment');
        let currentRating = 0;
        let currentImagePath = '';
    
        ratingBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                currentRating = parseInt(btn.dataset.rating);
                ratingBtns.forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
            });
        });
    
        submitBtn.addEventListener('click', () => {
            if (!currentRating) {
                alert('Please select a rating');
                return;
            }
    
            const feedback = {
                rating: currentRating,
                comment: commentInput.value,
                timestamp: new Date().toISOString(),
                imagePath: currentImagePath
            };
    
            saveFeedback(feedback);
        });
    }
    

    function displayFolderImages(folderName) {
        gallery.innerHTML = '';
        fetch(`/get_images/${folderName}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    data.images.forEach(image => {
                        const imgContainer = document.createElement('div');
                        imgContainer.className = 'preview-image-container';
    
                        const img = document.createElement('img');
                        img.src = `/get_image/${folderName}/${image}`;
                        img.alt = image;
                        img.className = 'preview-image';
    
                        // When an image is clicked, update the selected image info
                        imgContainer.addEventListener('click', () => {
                            // Update the selected image information
                            const selectedImageInfo = document.getElementById('selected-image-info');
                            selectedImageInfo.innerHTML = `
                                <p>Selected Image: ${image}</p>
                                <p>Folder: ${folderName}</p>
                            `;
                            
                            // Store the current selection in data attributes
                            const feedbackSection = document.getElementById('feedback-section');
                            feedbackSection.dataset.currentFolder = folderName;
                            feedbackSection.dataset.currentImage = image;
                            
                            // Load existing feedback for this image
                            loadPreviousFeedback(folderName, image);
                        });
    
                        const deleteBtn = document.createElement('button');
                        deleteBtn.className = 'remove-image';
                        deleteBtn.textContent = '×';
                        deleteBtn.onclick = (e) => {
                            e.stopPropagation();
                            deleteImage(folderName, image);
                        };
    
                        imgContainer.appendChild(img);
                        imgContainer.appendChild(deleteBtn);
                        gallery.appendChild(imgContainer);
                    });
                }
            })
            .catch(error => console.error('Error:', error));
    }
    
    function submitFeedback() {
        const feedbackSection = document.getElementById('feedback-section');
        const folderName = feedbackSection.dataset.currentFolder;
        const imageName = feedbackSection.dataset.currentImage;
        
        // Check if an image is selected
        if (!folderName || !imageName) {
            alert('Please select an image first');
            return;
        }
        
        const selectedRating = document.querySelector('.rating-btn.selected');
        const comment = document.getElementById('feedback-comment').value;
        
        if (!selectedRating) {
            alert('Please select a rating');
            return;
        }
        
        const feedback = {
            rating: parseInt(selectedRating.dataset.rating),
            comment: comment,
            timestamp: new Date().toISOString(),
            folderPath: folderName, // This ensures we're passing the folder path
            imageName: imageName
        };
    
        // Add console.log to debug the feedback object
        console.log('Submitting feedback:', feedback);
        
        saveFeedback(feedback);
    }
    
    function saveFeedback(feedback) {
        // Add console.log to debug the request
        console.log('Sending feedback data:', feedback);
    
        fetch('/save_feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(feedback)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Feedback saved successfully');
                // Refresh the feedback list
                loadPreviousFeedback(feedback.folderPath, feedback.imageName);
                
                // Clear the form
                document.querySelectorAll('.rating-btn').forEach(btn => btn.classList.remove('selected'));
                document.getElementById('feedback-comment').value = '';
            } else {
                alert('Error saving feedback: ' + (data.error || 'Unknown error'));
                console.error('Server response:', data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while saving feedback');
        });
    }
    
    function loadPreviousFeedback(folderName, imageName) {
        fetch(`/get_feedback/${folderName}/${imageName}`)
            .then(response => response.json())
            .then(data => {
                const feedbackList = document.getElementById('feedback-list');
                feedbackList.innerHTML = '';
                
                if (data.feedback && data.feedback.length > 0) {
                    data.feedback.forEach(item => {
                        const feedbackItem = document.createElement('div');
                        feedbackItem.className = 'feedback-item';
                        feedbackItem.innerHTML = `
                            <div class="feedback-header">
                                <span class="feedback-rating">Rating: ${item.rating}/10</span>
                                <span class="feedback-time">${new Date(item.timestamp).toLocaleString()}</span>
                            </div>
                            <div class="feedback-comment">${item.comment}</div>
                        `;
                        feedbackList.appendChild(feedbackItem);
                    });
                } else {
                    feedbackList.innerHTML = '<p>No feedback yet for this image.</p>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('feedback-list').innerHTML = 
                    '<p>Error loading feedback. Please try again later.</p>';
            });
    }

    function showFeedbackSection(folderName, imageName) {
        const feedbackSection = document.getElementById('feedback-section');
        feedbackSection.style.display = 'block';
        
        // Store current image information
        feedbackSection.dataset.currentFolder = folderName;
        feedbackSection.dataset.currentImage = imageName;
        
        // Reset previous feedback
        document.querySelectorAll('.rating-btn').forEach(btn => btn.classList.remove('selected'));
        document.getElementById('feedback-comment').value = '';
        
        // Load existing feedback for this image
        loadPreviousFeedback(folderName, imageName);
    }
});