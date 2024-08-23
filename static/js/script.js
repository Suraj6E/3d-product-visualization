document.addEventListener('DOMContentLoaded', (event) => {
    const fileInput = document.getElementById('file-input');
    const preview = document.getElementById('preview');
    const uploadForm = document.getElementById('upload-form');
    const uploadProgress = document.getElementById('upload-progress');

    fileInput.addEventListener('change', function(e) {
        preview.innerHTML = '';
        for (let i = 0; i < this.files.length; i++) {
            const file = this.files[i];
            if (!file.type.startsWith('image/')){ continue }
            const img = document.createElement('img');
            img.file = file;
            preview.appendChild(img);

            const reader = new FileReader();
            reader.onload = (function(aImg) { return function(e) { aImg.src = e.target.result; }; })(img);
            reader.readAsDataURL(file);
        }
    });

    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const xhr = new XMLHttpRequest();
        const formData = new FormData(this);

        xhr.upload.onprogress = function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                uploadProgress.value = percentComplete;
            }
        };

        xhr.onload = function() {
            if (xhr.status === 200) {
                window.location.reload();
            } else {
                alert('An error occurred during the upload. Please try again.');
            }
        };

        xhr.open('POST', this.action, true);
        xhr.send(formData);
    });
});