/**
 * Image Rotation Tool — 文件处理模块
 *
 * 文件选择、拖拽、PDF 解析、ONNX 方向检测、OCR 文字提取。
 */
window.ImageRotationFile = (function () {
    'use strict';

    var U = window.ImageRotationUtils;

    function handleFileSelect(event) {
        var files = Array.from(event.target.files);
        this.handleFiles(files);
        event.target.value = '';
    }

    function handleDrop(event) {
        this.isDragging = false;
        var files = Array.from(event.dataTransfer.files);
        this.handleFiles(files);
    }

    async function handleFiles(files) {
        this.errors = [];
        this.loading = true;
        this.loadingText = '正在处理文件...';
        this.progress = 0;

        var validImageFiles = [];
        var validPdfFiles = [];

        for (var fi = 0; fi < files.length; fi++) {
            var file = files[fi];
            if (this.SUPPORTED_FORMATS.indexOf(file.type) === -1) {
                this.errors.push('文件 ' + file.name + ' 格式不支持，已跳过');
                continue;
            }
            if (file.type === 'application/pdf') {
                if (file.size > this.MAX_PDF_SIZE) {
                    this.errors.push('文件 ' + file.name + ' 超过 50MB 限制，已跳过');
                    continue;
                }
                validPdfFiles.push(file);
            } else {
                if (file.size > this.MAX_SIZE) {
                    this.errors.push('文件 ' + file.name + ' 超过 20MB 限制，已跳过');
                    continue;
                }
                validImageFiles.push(file);
            }
        }

        var totalFiles = validImageFiles.length + validPdfFiles.length;
        var processedCount = 0;

        // 处理图片文件
        for (var i = 0; i < validImageFiles.length; i++) {
            processedCount++;
            this.progress = Math.round((processedCount / totalFiles) * 100);
            this.loadingText = '处理图片 (' + processedCount + '/' + totalFiles + ')...';
            try {
                var imageItem = await processFile(validImageFiles[i]);
                this.images.push(imageItem);
                await this.$nextTick();
                this.renderThumbnail(imageItem);
            } catch (err) {
                this.errors.push('文件 ' + validImageFiles[i].name + ' 处理失败: ' + err.message);
            }
        }

        // 处理 PDF 文件
        for (var j = 0; j < validPdfFiles.length; j++) {
            processedCount++;
            this.progress = Math.round((processedCount / totalFiles) * 100);
            this.loadingText = '处理 PDF (' + processedCount + '/' + totalFiles + ')...';
            try {
                await processPdfFile.call(this, validPdfFiles[j]);
            } catch (err) {
                this.errors.push('文件 ' + validPdfFiles[j].name + ' 处理失败: ' + err.message);
            }
        }

        // ONNX 方向检测
        var nonPdfImages = this.images.filter(function (img) { return img.sourceType !== 'pdf_page'; });
        if (nonPdfImages.length > 0) {
            await detectAllOrientationOnnx.call(this, nonPdfImages);
        } else {
            this.onnxComplete = true;
            await this.saveTaskToHistory();
        }

        this.progress = 100;
        this.loading = false;
    }

    async function processPdfFile(file) {
        var base64 = await U.fileToBase64(file);
        var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        var response = await fetch('/api/v1/image-rotation/extract-pdf-fast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ filename: file.name, data: base64 })
        });

        var result = await response.json();

        if (result.success) {
            var pdfPages = [];
            for (var i = 0; i < result.pages.length; i++) {
                var page = result.pages[i];
                var img = new Image();
                await new Promise(function (resolve, reject) {
                    img.onload = resolve;
                    img.onerror = reject;
                    img.src = page.data;
                });

                var imageItem = {
                    id: U.generateId(),
                    filename: file.name + '_page_' + page.page_number,
                    img: img,
                    data: page.data,
                    rotation: 0,
                    autoRotation: 0,
                    sourceType: 'pdf_page',
                    pdfFilename: file.name,
                    pageNumber: page.page_number,
                    format: 'png',
                    size: Math.round(page.data.length * 0.75),
                    status: 'detecting',
                    needsDetection: true,
                    detectionTimeMs: 0
                };

                this.images.push(imageItem);
                pdfPages.push(imageItem);
                await this.$nextTick();
                this.renderThumbnail(imageItem);
            }

            this.pdfPending += pdfPages.length;
            detectPdfPagesOrientationAsync.call(this, pdfPages);
        } else {
            throw new Error(result.message || 'PDF 解析失败');
        }
    }

    async function detectPdfPagesOrientationAsync(pages) {
        var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        for (var i = 0; i < pages.length; i++) {
            var page = pages[i];
            if (!page.needsDetection) { this.pdfPending = Math.max(0, this.pdfPending - 1); continue; }

            var idx = -1;
            for (var j = 0; j < this.images.length; j++) {
                if (this.images[j].id === page.id) { idx = j; break; }
            }
            if (idx === -1) { this.pdfPending = Math.max(0, this.pdfPending - 1); continue; }

            this.images[idx].status = 'detecting';

            try {
                var response = await fetch('/api/v1/image-rotation/detect-page-orientation', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                    body: JSON.stringify({ data: page.data })
                });
                var result = await response.json();

                if (result.rotation !== 0 && result.can_auto_rotate) {
                    this.images[idx].autoRotation = result.rotation;
                    this.images[idx].rotation = result.rotation;
                    this.renderThumbnail(this.images[idx]);
                }
                if (result.elapsed_ms !== undefined) {
                    this.images[idx].detectionTimeMs = result.elapsed_ms;
                }
                this.images[idx].status = 'processed';
                this.images[idx].needsDetection = false;
            } catch (err) {
                console.warn('检测 ' + page.filename + ' 方向失败:', err);
                this.images[idx].status = 'processed';
                this.images[idx].needsDetection = false;
            }

            this.pdfPending = Math.max(0, this.pdfPending - 1);
        }

        if (!this.currentJobId && this.images.length > 0) {
            await this.saveTaskToHistory();
        }
    }

    async function detectAllOrientationOnnx(images) {
        if (images.length === 0) return;

        var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        try {
            var payloadItems = [];
            for (var i = 0; i < images.length; i++) {
                var base64 = await U.fileToBase64(images[i].file);
                payloadItems.push({ filename: images[i].filename, data: base64, id: images[i].id });
            }

            this.loadingText = 'ONNX 方向检测中...';

            var response = await fetch('/api/v1/image-rotation/detect-orientation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ images: payloadItems, method: 'onnx' })
            });

            var result = await response.json();

            if (result.success && result.results) {
                for (var j = 0; j < result.results.length; j++) {
                    var detection = result.results[j];
                    var img = null;
                    for (var k = 0; k < images.length; k++) {
                        if (images[k].filename === detection.filename) { img = images[k]; break; }
                    }
                    if (!img) continue;

                    if (detection.elapsed_ms !== undefined) {
                        img.detectionTimeMs = detection.elapsed_ms;
                    }
                    if (detection.rotation !== 0 && detection.can_auto_rotate) {
                        img.autoRotation = detection.rotation;
                        img.rotation = detection.rotation;
                        img.detectionMethod = detection.method;
                        await this.$nextTick();
                        this.renderThumbnail(img);
                    }
                }
            }

            if (result.total_elapsed_ms !== undefined) {
                this.totalDetectionTimeMs = result.total_elapsed_ms;
            }

            this.showOcrPrompt = true;
            this.onnxComplete = true;
            await this.saveTaskToHistory();

        } catch (err) {
            console.warn('ONNX 方向检测失败:', err);
            this.onnxComplete = true;
        }
    }

    async function autoRenameFromOcr(items) {
        if (items.length === 0) return;

        var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        try {
            var response = await fetch('/api/v1/image-rotation/suggest-rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ items: items })
            });

            var result = await response.json();

            if (result.success && result.suggestions) {
                for (var i = 0; i < result.suggestions.length; i++) {
                    var suggestion = result.suggestions[i];
                    if (suggestion.success && suggestion.suggested_filename !== suggestion.original_filename) {
                        var img = null;
                        for (var j = 0; j < this.images.length; j++) {
                            if (this.images[j].filename === suggestion.original_filename) { img = this.images[j]; break; }
                        }
                        if (img) {
                            img.suggestedFilename = suggestion.suggested_filename;
                            img.extractedDate = suggestion.date;
                            img.extractedAmount = suggestion.amount;
                        }
                    }
                }
            }
        } catch (err) {
            console.warn('自动重命名失败:', err);
        }
    }

    async function startOcrExtraction(provider) {
        this.ocrProcessing = true;
        this.showOcrPrompt = false;
        this.loading = true;
        this.loadingText = provider === 'paddleocr_api' ? 'PaddleOCR API 提取文字中...' : '本地 OCR 提取文字中...';

        var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        var itemsForRename = [];

        try {
            for (var i = 0; i < this.images.length; i++) {
                var img = this.images[i];
                var base64 = await U.fileToBase64(img.file);

                var response = await fetch('/api/v1/image-rotation/extract-text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                    body: JSON.stringify({
                        images: [{ filename: img.filename, data: base64 }],
                        provider: provider
                    })
                });

                var result = await response.json();

                if (result.success && result.results && result.results[0]) {
                    var textResult = result.results[0];
                    if (textResult.ocr_text) {
                        img.ocrText = textResult.ocr_text;
                        itemsForRename.push({
                            filename: img.filename,
                            ocr_text: textResult.ocr_text,
                            image_data: base64,
                            rotation: img.rotation || 0
                        });
                    }
                }
            }

            if (itemsForRename.length > 0) {
                await autoRenameFromOcr.call(this, itemsForRename);
            }
        } catch (err) {
            console.warn('OCR 提取文字失败:', err);
            this.errors.push('OCR 提取文字失败: ' + err.message);
        } finally {
            this.ocrProcessing = false;
            this.loading = false;
        }
    }

    // 内部辅助：处理单个图片文件
    function processFile(file) {
        return new Promise(function (resolve, reject) {
            var reader = new FileReader();
            reader.onload = async function (e) {
                try {
                    var arrayBuffer = e.target.result;
                    var orientation = U.readExifOrientation(arrayBuffer);
                    var autoRotation = U.ORIENTATION_MAP[orientation] || 0;
                    var needsDetection = (orientation === 1);

                    var img = new Image();
                    img.onload = function () {
                        var format = file.type === 'image/png' ? 'png' : 'jpeg';
                        resolve({
                            id: U.generateId(),
                            file: file,
                            filename: file.name,
                            img: img,
                            rotation: autoRotation,
                            autoRotation: autoRotation,
                            needsDetection: needsDetection,
                            format: format,
                            size: file.size,
                            status: 'processed',
                            detectionTimeMs: 0
                        });
                    };
                    img.onerror = function () { reject(new Error('图片加载失败')); };
                    img.src = URL.createObjectURL(file);
                } catch (err) {
                    reject(err);
                }
            };
            reader.onerror = function () { reject(new Error('文件读取失败')); };
            reader.readAsArrayBuffer(file);
        });
    }

    return {
        handleFileSelect: handleFileSelect,
        handleDrop: handleDrop,
        handleFiles: handleFiles,
        processPdfFile: processPdfFile,
        detectAllOrientationOnnx: detectAllOrientationOnnx,
        startOcrExtraction: startOcrExtraction
    };
})();
