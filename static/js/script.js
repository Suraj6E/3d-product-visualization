document.addEventListener('DOMContentLoaded', (event) => {
    const fileInput = document.getElementById('file-input');
    const folderTitle = document.getElementById('folder-title');
    const preview = document.getElementById('preview');
    const gallery = document.getElementById('gallery');
    const foldersList = document.getElementById('folders-list');
    const saveFolderBtn = document.getElementById('save-folder');
    const folderSaveArea = document.getElementById('folder-save-area');

    let selectedFiles = [];

    fileInput.addEventListener('change', function(e) {
        const newFiles = Array.from(this.files);
        selectedFiles = [...selectedFiles, ...newFiles];
        updatePreview();
        folderSaveArea.style.display = 'block';
    });

    saveFolderBtn.addEventListener('click', function() {
        if (selectedFiles.length > 0 && folderTitle.value) {
            uploadFiles(selectedFiles, folderTitle.value);
        } else {
            alert('Please select files and enter a folder title before saving.');
        }
    });

    foldersList.addEventListener('click', function(e) {
        if (e.target.closest('.folder')) {
            const folderName = e.target.closest('.folder').dataset.folder;
            displayFolderImages(folderName);
        }
    });

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
                        const img = document.createElement('img');
                        img.src = `/get_image/${folderName}/${image}`;
                        img.alt = image;
                        img.className = 'gallery-image';
                        gallery.appendChild(img);
                    });
                } else {
                    console.error('Error:', data.message);
                }
            })
            .catch(error => console.error('Error:', error));
    }
});