document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');
    const processButton = document.getElementById('process-button');
    const processLoader = document.getElementById('process-loader');
    const uploadArea = document.getElementById('upload-area');
    const messageContainer = document.getElementById('message-container');
    const resultsContainer = document.getElementById('results-container');
    const resultsToggle = document.getElementById('results-toggle');
    const resultsContent = document.getElementById('results-content');
    const ocrResults = document.getElementById('ocr-results');
    const gpuInfo = document.getElementById('gpu-info');
    const deviceInfo = document.getElementById('device-info');
    const processingTime = document.getElementById('processing-time');
    
    // Maximum number of files allowed
    const MAX_FILES = 5;
    
    // Store file objects
    let files = [];
    
    // Check device info and display it
    fetchDeviceInfo();
    
    function fetchDeviceInfo() {
        fetch('/api/device-info')
            .then(response => response.json())
            .then(data => {
                deviceInfo.textContent = `Cihaz: ${data.device}`;
                
                if (data.device.toLowerCase().includes('cuda') || 
                    data.device.toLowerCase().includes('gpu')) {
                    gpuInfo.classList.add('gpu-active');
                    deviceInfo.innerHTML = `<strong>GPU modu aktif:</strong> ${data.device}`;
                } else {
                    gpuInfo.classList.add('cpu-active');
                    deviceInfo.innerHTML = `<strong>CPU modu aktif:</strong> ${data.device}`;
                }
            })
            .catch(error => {
                console.error('Error fetching device info:', error);
                deviceInfo.textContent = 'Cihaz: CPU (varsayılan)';
                gpuInfo.classList.add('cpu-active');
            });
    }
    
    // Toggle results dropdown
    resultsToggle.addEventListener('click', function() {
        resultsContent.classList.toggle('open');
        const icon = resultsToggle.querySelector('i');
        if (resultsContent.classList.contains('open')) {
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
        } else {
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-down');
        }
    });
    
    // Add event listeners for drag and drop
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.style.borderColor = '#3498db';
    });
    
    uploadArea.addEventListener('dragleave', function() {
        uploadArea.style.borderColor = '#ccc';
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.style.borderColor = '#ccc';
        
        const droppedFiles = e.dataTransfer.files;
        handleFiles(droppedFiles);
    });
    
    // Add event listener for file input
    fileInput.addEventListener('change', function() {
        handleFiles(fileInput.files);
        fileInput.value = '';  // Reset file input
    });
    
    // Handle the selected files
    function handleFiles(selectedFiles) {
        if (files.length + selectedFiles.length > MAX_FILES) {
            showMessage(`En fazla ${MAX_FILES} dosya yükleyebilirsiniz.`, 'error');
            return;
        }
        
        for (let i = 0; i < selectedFiles.length; i++) {
            const file = selectedFiles[i];
            
            // Check if file is an image
            if (!file.type.match('image.*')) {
                showMessage('Lütfen sadece resim dosyası yükleyin.', 'error');
                continue;
            }
            
            // Check if file already exists
            const fileExists = files.some(existingFile => existingFile.name === file.name);
            if (fileExists) {
                showMessage(`${file.name} zaten listeye eklenmiş.`, 'error');
                continue;
            }
            
            // Add file to array
            files.push({
                file: file,
                status: 'pending',
                pdfUrl: null
            });
            
            // Update UI
            updateFileList();
        }
        
        // Enable/disable process button
        processButton.disabled = files.length === 0;
    }
    
    // Update the file list UI
    function updateFileList() {
        fileList.innerHTML = '';
        
        files.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = file.text ? 'file-item with-text' : 'file-item';
            
            const statusClass = file.status === 'completed' ? 'completed' : 
                              file.status === 'processing' ? 'processing' : 
                              file.status === 'error' ? 'error' : 'pending';
            
            fileItem.innerHTML = `
                <i class="fas fa-file-alt file-icon"></i>
                <span class="file-name">${file.file.name}</span>
                <span class="file-status ${statusClass}">${file.status}</span>
            `;
            
            // Add PDF link for completed files
            if (file.status === 'completed' && file.pdfUrl) {
                const pdfButton = document.createElement('a');
                pdfButton.href = file.pdfUrl;
                pdfButton.className = 'view-pdf-button';
                pdfButton.textContent = 'PDF';
                pdfButton.target = '_blank';
                fileItem.appendChild(pdfButton);
            }
            
            // Add toggle text button for files with OCR results
            if (file.text) {
                const toggleButton = document.createElement('span');
                toggleButton.className = 'toggle-text';
                toggleButton.textContent = 'Metni Göster';
                toggleButton.addEventListener('click', function() {
                    fileItem.classList.toggle('expanded');
                    toggleButton.textContent = fileItem.classList.contains('expanded') ? 'Metni Gizle' : 'Metni Göster';
                });
                fileItem.appendChild(toggleButton);
                
                // Add text container
                const textContainer = document.createElement('div');
                textContainer.className = 'file-text';
                textContainer.innerHTML = `<pre>${file.text}</pre>`;
                fileItem.appendChild(textContainer);
            }
            
            // Add remove button
            const removeButton = document.createElement('button');
            removeButton.className = 'remove-button';
            removeButton.textContent = 'Sil';
            removeButton.addEventListener('click', function() {
                files.splice(index, 1);
                updateFileList();
                processButton.disabled = files.length === 0;
            });
            fileItem.appendChild(removeButton);
            
            // Add progress bar for processing files
            if (file.status === 'processing') {
                const progressBarContainer = document.createElement('div');
                progressBarContainer.className = 'progress-bar-container';
                
                const progressBar = document.createElement('div');
                progressBar.className = 'progress-bar';
                progressBar.style.width = '100%';
                
                progressBarContainer.appendChild(progressBar);
                fileItem.appendChild(progressBarContainer);
            }
            
            fileList.appendChild(fileItem);
        });
    }
    
    // Event listener for process button
    processButton.addEventListener('click', function() {
        processFiles();
    });
    
    // Process files with OCR
    async function processFiles() {
        if (files.length === 0) {
            return;
        }
        
        // Disable button and show loader
        processButton.disabled = true;
        processLoader.style.display = 'inline-block';
        
        try {
            // Process each file
            let allTexts = [];
            let totalTime = 0;
            let fileCount = 0;
            
            for (let i = 0; i < files.length; i++) {
                if (files[i].status !== 'completed') {
                    files[i].status = 'processing';
                    updateFileList();
                    
                    try {
                        const startTime = performance.now();
                        const result = await processFile(files[i].file);
                        const endTime = performance.now();
                        const processingTimeMs = endTime - startTime;
                        
                        totalTime += processingTimeMs;
                        fileCount++;
                        
                        files[i].status = 'completed';
                        files[i].pdfUrl = result.pdfUrl;
                        files[i].text = result.text || '';
                        files[i].processingTime = processingTimeMs;
                        
                        // Add file name and text to results
                        if (files[i].text) {
                            allTexts.push(`--- ${files[i].file.name} (${(processingTimeMs/1000).toFixed(2)}s) ---\n${files[i].text}\n`);
                        }
                        
                    } catch (error) {
                        console.error('Error processing file:', error);
                        files[i].status = 'error';
                    }
                    
                    updateFileList();
                } else {
                    // For already completed files, add their text to results
                    if (files[i].text) {
                        const timeInfo = files[i].processingTime ? 
                            ` (${(files[i].processingTime/1000).toFixed(2)}s)` : '';
                        allTexts.push(`--- ${files[i].file.name}${timeInfo} ---\n${files[i].text}\n`);
                    }
                }
            }
            
            // Update and show the OCR results
            if (allTexts.length > 0) {
                ocrResults.innerHTML = `<pre>${allTexts.join('\n')}</pre>`;
                resultsContainer.style.display = 'block';
                resultsContent.classList.add('open');
                const icon = resultsToggle.querySelector('i');
                icon.classList.remove('fa-chevron-down');
                icon.classList.add('fa-chevron-up');
            }
            
            // Display average processing time
            if (fileCount > 0) {
                const avgTime = totalTime / fileCount;
                processingTime.innerHTML = `<strong>Ortalama işlem süresi:</strong> ${(avgTime/1000).toFixed(2)} saniye`;
            }
            
            showMessage('Tüm dosyalar işlendi!', 'success');
        } catch (error) {
            console.error('Error during processing:', error);
            showMessage('İşlem sırasında bir hata oluştu.', 'error');
        } finally {
            // Enable button and hide loader
            processButton.disabled = false;
            processLoader.style.display = 'none';
        }
    }
    
    // Process a single file
    async function processFile(file) {
        return new Promise(async (resolve, reject) => {
            try {
                const formData = new FormData();
                formData.append('image', file);
                formData.append('langs', 'tr,en');
                
                const response = await fetch('/api/ocr', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('OCR işlemi başarısız oldu.');
                }
                
                const data = await response.json();
                
                // Check if the operation was successful
                if (data.error) {
                    throw new Error(data.error);
                }
                
                resolve({
                    text: data.text || '',
                    pdfUrl: data.pdfUrl || '/pdf/' + file.name.replace(/\.[^/.]+$/, '_ocr.pdf')
                });
            } catch (error) {
                reject(error);
            }
        });
    }
    
    // Show a message to the user
    function showMessage(message, type) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}`;
        messageElement.textContent = message;
        
        messageContainer.innerHTML = '';
        messageContainer.appendChild(messageElement);
        
        // Remove the message after 5 seconds
        setTimeout(() => {
            messageElement.remove();
        }, 5000);
    }
}); 