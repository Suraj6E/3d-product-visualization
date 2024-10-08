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

                        const deleteBtn = document.createElement('button');
                        deleteBtn.className = 'remove-image';
                        deleteBtn.textContent = 'X';
                        deleteBtn.onclick = () => deleteImage(folderName, image);

                        imgContainer.appendChild(img);
                        imgContainer.appendChild(deleteBtn);
                        gallery.appendChild(imgContainer);
                    });
                } else {
                    console.error('Error:', data.message);
                }
            })
            .catch(error => console.error('Error:', error));
    }

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
});