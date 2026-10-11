// ============================================================
// FILE: static/js/main.js
// HỆ THỐNG GIÁM SÁT & ĐẾM XE BÃI ĐỖ THÔNG MINH
// TƯƠNG THÍCH ĐÁM MÂY VERCEL SERVERLESS & MÁY CỤC BỘ
// ============================================================

// Biến trạng thái toàn cục
let currentMode = "demo";         // 'demo' | 'webcam' | 'upload' | 'filters'
let uploadedFilePath = null;      // Đường dẫn file đã upload lên server
let uploadedFileObject = null;    // Đối tượng File tải lên
let statsTimer = null;            // ID timer polling thống kê
let webcamStream = null;          // Luồng video HTML5 từ camera trình duyệt
let webcamFrameTimer = null;      // Timer gửi frame webcam lên server
let isRunning = false;            // Cờ trạng thái đang giám sát

const URL_ROOT = (document.body && document.body.dataset.urlRoot) ? document.body.dataset.urlRoot : "";
function getApiUrl(path) {
    return URL_ROOT + path;
}

// ------------------------------------------------------------
// 1. QUẢN LÝ CHẾ ĐỘ NGUỒN (DEMO / WEBCAM / UPLOAD / FILTERS)
// ------------------------------------------------------------
function setSourceMode(mode) {
    currentMode = mode;

    // Cập nhật tab active
    document.querySelectorAll(".mode-tab").forEach(tab => {
        if (tab.dataset.mode === mode) {
            tab.classList.add("active");
        } else {
            tab.classList.remove("active");
        }
    });

    // Ẩn/hiện các khung cấu hình
    document.getElementById("inputDemoBox").style.display = (mode === "demo") ? "flex" : "none";
    document.getElementById("inputWebcamBox").style.display = (mode === "webcam") ? "flex" : "none";
    document.getElementById("inputUploadBox").style.display = (mode === "upload") ? "flex" : "none";
    document.getElementById("inputFiltersBox").style.display = (mode === "filters") ? "flex" : "none";

    const filterBox = document.getElementById("filterExplanationBox");
    if (mode !== "filters") {
        filterBox.style.display = "none";
    }

    addLog(`Đã chuyển sang chế độ: ${mode.toUpperCase()}`, "info");

    if (mode === "demo") {
        runInstantDemo();
    }
}

// Cập nhật text slider độ tin cậy
function updateConfText(val) {
    document.getElementById("confValueText").textContent = `${val}%`;
}

// ------------------------------------------------------------
// 2. CHẠY DEMO MẪU TỨC THÌ (1-CLICK INSTANT DEMO)
// ------------------------------------------------------------
function runInstantDemo() {
    addLog("Đang nạp dữ liệu phân tích bãi đỗ xe mẫu...", "info");

    fetch(getApiUrl("/api/sample_demo"))
        .then(res => res.json())
        .then(data => {
            if (data.status === "success") {
                const videoFeed = document.getElementById("videoFeed");
                const placeholder = document.getElementById("videoPlaceholder");
                const webcamVideo = document.getElementById("webcamVideo");

                webcamVideo.style.display = "none";
                placeholder.style.display = "none";
                videoFeed.style.display = "block";
                videoFeed.src = data.annotated_url + "?t=" + Date.now();

                // Cập nhật số liệu thống kê
                updateStatsDisplay(data.counts, data.total, data.occupancy_rate, data.available_slots);

                addLog(`✅ Phân tích mẫu hoàn tất: ${data.total} phương tiện (Ô tô: ${data.counts.car}, Xe tải: ${data.counts.truck})`, "success");
                setRunningState(true);
            }
        })
        .catch(err => {
            addLog("Lỗi nạp demo: " + err.message, "error");
        });
}

// ------------------------------------------------------------
// 3. THÍ NGHIỆM BỘ LỌC XỬ LÝ ẢNH (CANNY, SOBEL, OTSU,...)
// ------------------------------------------------------------
function applyImageFilter(filterName) {
    addLog(`Đang áp dụng thuật toán xử lý ảnh: ${filterName.toUpperCase()}...`, "info");

    fetch(getApiUrl("/api/image_filter"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filter: filterName })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            const videoFeed = document.getElementById("videoFeed");
            const placeholder = document.getElementById("videoPlaceholder");
            const webcamVideo = document.getElementById("webcamVideo");
            const filterBox = document.getElementById("filterExplanationBox");
            const filterText = document.getElementById("filterExplanationText");

            webcamVideo.style.display = "none";
            placeholder.style.display = "none";
            videoFeed.style.display = "block";
            videoFeed.src = data.image_b64;

            filterBox.style.display = "block";
            filterText.textContent = data.explanation;

            addLog(`✅ Đã hiển thị kết quả thuật toán ${filterName.toUpperCase()}`, "success");
        } else {
            addLog(`Lỗi xử lý bộ lọc: ${data.error}`, "error");
        }
    })
    .catch(err => {
        addLog(`Lỗi kết nối bộ lọc: ${err.message}`, "error");
    });
}

// ------------------------------------------------------------
// 4. XỬ LÝ TẢI FILE (ẢNH HOẶC VIDEO)
// ------------------------------------------------------------
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    uploadedFileObject = file;
    const fileNameLabel = document.getElementById("uploadFileName");
    fileNameLabel.textContent = `Đang nạp: ${file.name}...`;

    if (file.type.startsWith("image/")) {
        // Nếu là file ảnh: Phân tích trực tiếp qua API
        addLog(`Đang phân tích ảnh "${file.name}"...`, "info");
        const formData = new FormData();
        formData.append("image", file);
        formData.append("confidence", (parseInt(document.getElementById("confSlider").value, 10) / 100).toString());

        fetch(getApiUrl("/api/analyze_image"), {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === "success") {
                const videoFeed = document.getElementById("videoFeed");
                const placeholder = document.getElementById("videoPlaceholder");
                const webcamVideo = document.getElementById("webcamVideo");

                webcamVideo.style.display = "none";
                placeholder.style.display = "none";
                videoFeed.style.display = "block";
                videoFeed.src = data.image_b64;

                updateStatsDisplay(data.counts, data.total);
                fileNameLabel.textContent = `✅ ${file.name}`;
                fileNameLabel.style.color = "#34d399";
                addLog(`✅ Phân tích ảnh thành công! Phát hiện: ${data.total} phương tiện.`, "success");
                setRunningState(true);
            } else {
                throw new Error(data.error || "Lỗi xử lý ảnh");
            }
        })
        .catch(err => {
            fileNameLabel.textContent = "❌ Lỗi xử lý";
            fileNameLabel.style.color = "#f87171";
            addLog(`Lỗi: ${err.message}`, "error");
        });

    } else {
        // Nếu là video: Tải lên máy chủ
        const formData = new FormData();
        formData.append("video", file);

        fetch(getApiUrl("/api/upload"), {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            uploadedFilePath = data.file_path;
            fileNameLabel.textContent = `✅ ${data.filename}`;
            fileNameLabel.style.color = "#34d399";
            addLog(`Đã tải lên video thành công: ${data.filename}`, "success");
        })
        .catch(err => {
            fileNameLabel.textContent = "❌ Lỗi tải lên";
            fileNameLabel.style.color = "#f87171";
            addLog(`Lỗi upload: ${err.message}`, "error");
        });
    }
}

// ------------------------------------------------------------
// 5. KHỞI ĐỘNG NHẬN DIỆN (START)
// ------------------------------------------------------------
function startDetection() {
    if (isRunning) return;

    if (currentMode === "demo") {
        runInstantDemo();
        return;
    }

    if (currentMode === "filters") {
        applyImageFilter("canny");
        return;
    }

    if (currentMode === "webcam") {
        startBrowserWebcam();
        return;
    }

    if (currentMode === "upload") {
        if (!uploadedFileObject) {
            alert("Vui lòng bấm 'Chọn Ảnh / Video Bãi Đỗ' trước khi bắt đầu!");
            return;
        }
        addLog("Đang xử lý nội dung tải lên...", "info");
    }
}

// ------------------------------------------------------------
// 6. XỬ LÝ CAMERA TRÌNH DUYỆT (HTML5 WEBCAM CHO CLOUD/VERCEL)
// ------------------------------------------------------------
function startBrowserWebcam() {
    addLog("Đang yêu cầu quyền truy cập Camera thiết bị...", "info");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        addLog("Trình duyệt không hỗ trợ MediaDevices API. Đang chuyển sang luồng camera máy chủ...", "warning");
        fallbackServerStream();
        return;
    }

    navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
        .then(stream => {
            webcamStream = stream;
            const webcamVideo = document.getElementById("webcamVideo");
            const videoFeed = document.getElementById("videoFeed");
            const placeholder = document.getElementById("videoPlaceholder");

            placeholder.style.display = "none";
            videoFeed.style.display = "none";
            webcamVideo.style.display = "block";
            webcamVideo.srcObject = stream;

            setRunningState(true);
            addLog("Camera thiết bị đã kết nối thành công. Bắt đầu phân tích khung hình...", "success");

            // Khởi chạy vòng lặp bắt frame từ canvas gửi lên API xử lý
            const canvas = document.getElementById("hiddenCanvas");
            const ctx = canvas.getContext("2d");

            webcamFrameTimer = setInterval(() => {
                if (!isRunning || !webcamStream) return;
                if (webcamVideo.videoWidth === 0) return;

                canvas.width = 480;
                canvas.height = 360;
                ctx.drawImage(webcamVideo, 0, 0, canvas.width, canvas.height);
                const frameB64 = canvas.toDataURL("image/jpeg", 0.7);

                fetch(getApiUrl("/api/process_frame"), {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        frame: frameB64,
                        confidence: parseInt(document.getElementById("confSlider").value, 10) / 100
                    })
                })
                .then(r => r.json())
                .then(data => {
                    if (data.status === "success") {
                        updateStatsDisplay(data.counts, data.total);
                        if (data.fps) document.getElementById("fpsDisplay").textContent = data.fps.toFixed(1);
                    }
                })
                .catch(() => {});
            }, 800); // Mỗi 800ms phân tích 1 frame
        })
        .catch(err => {
            addLog(`Không thể mở Camera trình duyệt (${err.name}). Dùng camera máy chủ...`, "warning");
            fallbackServerStream();
        });
}

function fallbackServerStream() {
    const confVal = parseInt(document.getElementById("confSlider").value, 10) / 100;
    fetch(getApiUrl("/api/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: 0, confidence: confVal })
    })
    .then(r => r.json())
    .then(() => {
        const videoFeed = document.getElementById("videoFeed");
        const placeholder = document.getElementById("videoPlaceholder");
        placeholder.style.display = "none";
        videoFeed.style.display = "block";
        videoFeed.src = getApiUrl("/video_feed?t=" + Date.now());
        setRunningState(true);
        startStatsPolling();
    })
    .catch(e => addLog("Lỗi: " + e.message, "error"));
}

// ------------------------------------------------------------
// 7. DỪNG NHẬN DIỆN (STOP)
// ------------------------------------------------------------
function stopDetection() {
    if (!isRunning) return;

    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }
    if (webcamFrameTimer) {
        clearInterval(webcamFrameTimer);
        webcamFrameTimer = null;
    }
    if (statsTimer) {
        clearInterval(statsTimer);
        statsTimer = null;
    }

    fetch(getApiUrl("/api/stop"), { method: "POST" }).catch(() => {});

    setRunningState(false);
    addLog("Đã tạm dừng tiến trình giám sát.", "info");
}

function setRunningState(running) {
    isRunning = running;
    document.getElementById("btnStart").disabled = running;
    document.getElementById("btnStop").disabled = !running;

    const statusPill = document.getElementById("systemStatus");
    const statusLabel = document.getElementById("statusLabel");
    if (running) {
        statusPill.className = "status-pill status-online";
        statusLabel.textContent = "Đang Giám Sát";
    } else {
        statusPill.className = "status-pill status-offline";
        statusLabel.textContent = "Tạm Dừng";
    }
}

// ------------------------------------------------------------
// 8. CẬP NHẬT GIAO DIỆN THỐNG KÊ (STATS DISPLAY)
// ------------------------------------------------------------
function updateStatsDisplay(counts, total, occupancyRate = null, availableSlots = null) {
    if (!counts) return;

    document.getElementById("totalCount").textContent = total;
    document.getElementById("carCount").textContent = counts.car || 0;
    document.getElementById("motorcycleCount").textContent = counts.motorcycle || 0;
    document.getElementById("busCount").textContent = counts.bus || 0;
    document.getElementById("truckCount").textContent = counts.truck || 0;

    const capacity = 50;
    const occ = occupancyRate || (Math.min(100, Math.round((total / capacity) * 100)) + "%");
    const avail = (availableSlots !== null) ? availableSlots : Math.max(0, capacity - total);

    const occElem = document.getElementById("occupancyRate");
    const availElem = document.getElementById("availableSlots");
    const barElem = document.getElementById("occupancyBar");

    if (occElem) occElem.textContent = occ;
    if (availElem) availElem.textContent = avail;
    if (barElem) barElem.style.width = occ;
}

function startStatsPolling() {
    if (statsTimer) clearInterval(statsTimer);
    statsTimer = setInterval(() => {
        if (!isRunning) return;
        fetch(getApiUrl("/api/stats"))
            .then(r => r.json())
            .then(data => {
                if (data.counts) {
                    updateStatsDisplay(data.counts, data.total);
                    if (data.fps) document.getElementById("fpsDisplay").textContent = data.fps.toFixed(1);
                }
            })
            .catch(() => {});
    }, 1000);
}

// ------------------------------------------------------------
// 9. NHẬT KÝ HOẠT ĐỘNG (ACTIVITY LOG)
// ------------------------------------------------------------
function addLog(msg, type = "info") {
    const logBox = document.getElementById("activityLog");
    if (!logBox) return;

    const now = new Date();
    const timeStr = [
        String(now.getHours()).padStart(2, "0"),
        String(now.getMinutes()).padStart(2, "0"),
        String(now.getSeconds()).padStart(2, "0")
    ].join(":");

    const entry = document.createElement("div");
    entry.className = `log-entry log-${type}`;
    entry.innerHTML = `<span class="log-time">${timeStr}</span> <span class="log-msg">${msg}</span>`;

    logBox.insertBefore(entry, logBox.firstChild);

    while (logBox.children.length > 50) {
        logBox.removeChild(logBox.lastChild);
    }
}

function clearLogs() {
    const logBox = document.getElementById("activityLog");
    if (logBox) logBox.innerHTML = "";
    addLog("Đã làm mới nhật ký hoạt động.", "info");
}

// Tự động kích hoạt khi trang tải xong
window.addEventListener("DOMContentLoaded", () => {
    addLog("Hệ thống kết nối Vercel Serverless thành công.", "success");
    runInstantDemo();
});
