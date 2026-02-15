/**
 * ACMS Desktop - File Upload Component
 *
 * Sprint 3 Day 13: File Upload capability
 *
 * Features:
 * - Drag-and-drop file upload zone
 * - File picker button
 * - Support for PDF, TXT, MD, images, JSON
 * - Upload progress indicator
 * - Preview of uploaded files
 */

const API_BASE_URL = 'http://localhost:40080';

// Allowed file types
const ALLOWED_TYPES = {
    'text/plain': '.txt',
    'text/markdown': '.md',
    'application/pdf': '.pdf',
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'application/json': '.json'
};

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

/**
 * Upload file to server
 * @param {File} file - File to upload
 * @param {Object} options - Upload options
 * @returns {Promise<Object>} Upload result
 */
async function uploadFile(file, options = {}) {
    const formData = new FormData();
    formData.append('file', file);

    if (options.user_id) {
        formData.append('user_id', options.user_id);
    }
    if (options.privacy_level) {
        formData.append('privacy_level', options.privacy_level);
    }
    if (options.save_to_memory !== undefined) {
        formData.append('save_to_memory', options.save_to_memory);
    }
    if (options.conversation_id) {
        formData.append('conversation_id', options.conversation_id);
    }

    try {
        const response = await fetch(`${API_BASE_URL}/gateway/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        return await response.json();
    } catch (error) {
        console.error('Upload error:', error);
        throw error;
    }
}

/**
 * Validate file before upload
 * @param {File} file - File to validate
 * @returns {Object} Validation result
 */
function validateFile(file) {
    // Check file type
    if (!ALLOWED_TYPES[file.type]) {
        return {
            valid: false,
            error: `File type not supported: ${file.type}. Allowed: ${Object.values(ALLOWED_TYPES).join(', ')}`
        };
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
        return {
            valid: false,
            error: `File too large: ${(file.size / 1024 / 1024).toFixed(2)}MB. Maximum: ${MAX_FILE_SIZE / 1024 / 1024}MB`
        };
    }

    return { valid: true };
}

/**
 * Create file upload button for input area
 * @param {Function} onFileSelected - Callback when file is selected
 * @returns {HTMLElement} Upload button element
 */
function createUploadButton(onFileSelected) {
    const button = document.createElement('button');
    button.className = 'file-upload-btn';
    button.type = 'button';
    button.title = 'Upload file (PDF, TXT, MD, images)';
    button.innerHTML = `<span class="upload-icon">&#x1F4CE;</span>`;

    // Hidden file input
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = Object.keys(ALLOWED_TYPES).join(',');
    fileInput.style.display = 'none';

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const validation = validateFile(file);
            if (validation.valid) {
                onFileSelected(file);
            } else {
                alert(validation.error);
            }
        }
        // Reset input so same file can be selected again
        fileInput.value = '';
    });

    button.addEventListener('click', () => fileInput.click());
    button.appendChild(fileInput);

    return button;
}

/**
 * Create drag-and-drop zone
 * @param {HTMLElement} targetElement - Element to make droppable
 * @param {Function} onFileDrop - Callback when file is dropped
 */
function setupDragAndDrop(targetElement, onFileDrop) {
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {
        targetElement.addEventListener(event, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    // Highlight drop zone
    ['dragenter', 'dragover'].forEach(event => {
        targetElement.addEventListener(event, () => {
            targetElement.classList.add('drag-active');
        });
    });

    // Remove highlight
    ['dragleave', 'drop'].forEach(event => {
        targetElement.addEventListener(event, () => {
            targetElement.classList.remove('drag-active');
        });
    });

    // Handle drop
    targetElement.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            const validation = validateFile(file);
            if (validation.valid) {
                onFileDrop(file);
            } else {
                alert(validation.error);
            }
        }
    });
}

/**
 * Create file preview element
 * @param {File} file - File to preview
 * @param {Function} onRemove - Callback when remove is clicked
 * @returns {HTMLElement} Preview element
 */
function createFilePreview(file, onRemove) {
    const preview = document.createElement('div');
    preview.className = 'file-preview';

    // File icon based on type
    let icon = '\u{1F4C4}'; // Default document
    if (file.type.startsWith('image/')) {
        icon = '\u{1F5BC}'; // Image
    } else if (file.type === 'application/pdf') {
        icon = '\u{1F4D1}'; // PDF
    } else if (file.type === 'application/json') {
        icon = '\u{1F4DD}'; // JSON
    }

    preview.innerHTML = `
        <span class="file-icon">${icon}</span>
        <div class="file-info">
            <span class="file-name">${file.name}</span>
            <span class="file-size">${formatFileSize(file.size)}</span>
        </div>
        <button class="file-remove" title="Remove file">&times;</button>
    `;

    preview.querySelector('.file-remove').addEventListener('click', onRemove);

    return preview;
}

/**
 * Create upload progress indicator
 * @param {string} filename - Name of file being uploaded
 * @returns {Object} Progress element and update function
 */
function createUploadProgress(filename) {
    const progress = document.createElement('div');
    progress.className = 'upload-progress';
    progress.innerHTML = `
        <div class="upload-progress-text">Uploading ${filename}...</div>
        <div class="upload-progress-bar">
            <div class="upload-progress-fill" style="width: 0%"></div>
        </div>
    `;

    const fill = progress.querySelector('.upload-progress-fill');
    const text = progress.querySelector('.upload-progress-text');

    return {
        element: progress,
        update: (percent) => {
            fill.style.width = `${percent}%`;
        },
        complete: (success, message) => {
            text.textContent = message || (success ? 'Upload complete!' : 'Upload failed');
            progress.classList.add(success ? 'success' : 'error');
            fill.style.width = '100%';
        }
    };
}

/**
 * Format file size for display
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted size
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

/**
 * Get file type label
 * @param {string} mimeType - MIME type
 * @returns {string} Human-readable label
 */
function getFileTypeLabel(mimeType) {
    const labels = {
        'text/plain': 'Text File',
        'text/markdown': 'Markdown',
        'application/pdf': 'PDF Document',
        'image/png': 'PNG Image',
        'image/jpeg': 'JPEG Image',
        'image/gif': 'GIF Image',
        'image/webp': 'WebP Image',
        'application/json': 'JSON File'
    };
    return labels[mimeType] || 'File';
}

module.exports = {
    uploadFile,
    validateFile,
    createUploadButton,
    setupDragAndDrop,
    createFilePreview,
    createUploadProgress,
    formatFileSize,
    getFileTypeLabel,
    ALLOWED_TYPES,
    MAX_FILE_SIZE
};
