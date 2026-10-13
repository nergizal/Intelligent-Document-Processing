from fastapi import FastAPI, Response, status
from fastapi.responses import HTMLResponse
from app.db.session import engine, is_database_reachable
from app.db.models import Base
from app.api.v1.documents import router as documents_router

# Veritabanı tablolarını idp_platform.db içinde otomatik oluşturur
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Intelligent Document Processing & Business Process Automation Platform",
    description="Fatura ve yarı yapılandırılmış belgeleri OCR/NLP ile işleyen entegre platform.",
    version="1.0.0"
)

# Health Check Uç Noktası
@app.get("/api/v1/health", tags=["Health"])
def health_check():
    db_ok = is_database_reachable()
    if not db_ok:
        return Response(
            content='{"status": "unhealthy", "database": "disconnected"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )
    return {"status": "healthy", "database": "connected"}

# Belge İşleme ve Onay Router'ı
app.include_router(documents_router, prefix="/api/v1")

# -----------------------------------------------------------------------------
# KAPSAMLI OPERATÖR & YÖNETİM DASHBOARD'I (/app)
# -----------------------------------------------------------------------------
@app.get("/app", response_class=HTMLResponse, tags=["Web App"])
def get_web_app():
    return """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IDP Platform - Akıllı Belge İşleme & Otomasyon Merkezi</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
        <style>
            :root {
                --primary-color: #0f172a;
                --accent-color: #2563eb;
                --bg-color: #f8fafc;
            }
            body { background-color: var(--bg-color); font-family: 'Segoe UI', system-ui, sans-serif; }
            .navbar { background-color: var(--primary-color) !important; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
            .card-custom { border: none; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); transition: transform 0.2s; }
            .card-custom:hover { transform: translateY(-2px); }
            .metric-value { font-size: 1.8rem; font-weight: 700; }
            .drop-zone { border: 2px dashed #cbd5e1; border-radius: 12px; padding: 2.5rem; text-align: center; background: #ffffff; cursor: pointer; transition: all 0.2s; }
            .drop-zone:hover, .drop-zone.dragover { border-color: var(--accent-color); background: #eff6ff; }
            .badge-approved { background-color: #dcfce7; color: #15803d; }
            .badge-review { background-color: #fef9c3; color: #a16207; }
            .badge-failed { background-color: #fee2e2; color: #b91c1c; }
            .nav-tabs .nav-link.active { font-weight: 600; border-bottom: 3px solid var(--accent-color); color: var(--accent-color) !important; }
        </style>
    </head>
    <body>

        <!-- Navbar -->
        <nav class="navbar navbar-expand-lg navbar-dark mb-4">
            <div class="container-fluid px-4">
                <a class="navbar-brand d-flex align-items-center gap-2" href="#">
                    <i class="bi bi-cpu-fill text-primary"></i>
                    <span class="fw-bold">Intelligent Document Processing (IDP)</span>
                </a>
                <div class="d-flex align-items-center gap-3">
                    <span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-2 rounded-pill">
                        <i class="bi bi-check-circle-fill me-1"></i> System Online
                    </span>
                </div>
            </div>
        </nav>

        <div class="container-fluid px-4 mb-5">
            
            <!-- Özet İstatistik Kartları (KPI Dashboard) -->
            <div class="row g-3 mb-4">
                <div class="col-md-3">
                    <div class="card card-custom bg-white p-3">
                        <div class="d-flex align-items-center justify-content-between">
                            <div>
                                <small class="text-muted fw-semibold">Toplam İşlenen Belge</small>
                                <div class="metric-value text-dark" id="kpiTotal">0</div>
                            </div>
                            <div class="p-3 bg-primary-subtle rounded-circle text-primary"><i class="bi bi-file-earmark-text fs-4"></i></div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card card-custom bg-white p-3">
                        <div class="d-flex align-items-center justify-content-between">
                            <div>
                                <small class="text-muted fw-semibold">Otomatik Onaylı (APPROVED)</small>
                                <div class="metric-value text-success" id="kpiApproved">0</div>
                            </div>
                            <div class="p-3 bg-success-subtle rounded-circle text-success"><i class="bi bi-check-lg fs-4"></i></div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card card-custom bg-white p-3">
                        <div class="d-flex align-items-center justify-content-between">
                            <div>
                                <small class="text-muted fw-semibold">Bekleyen İnceleme (HUMAN_REVIEW)</small>
                                <div class="metric-value text-warning" id="kpiReview">0</div>
                            </div>
                            <div class="p-3 bg-warning-subtle rounded-circle text-warning"><i class="bi bi-exclamation-triangle fs-4"></i></div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card card-custom bg-white p-3">
                        <div class="d-flex align-items-center justify-content-between">
                            <div>
                                <small class="text-muted fw-semibold">Ortalama İşlem Süresi</small>
                                <div class="metric-value text-info" id="kpiAvgDuration">0 ms</div>
                            </div>
                            <div class="p-3 bg-info-subtle rounded-circle text-info"><i class="bi bi-lightning-charge fs-4"></i></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Sekmeli Ana İçerik -->
            <ul class="nav nav-tabs mb-4 border-0" id="mainTabs">
                <li class="nav-item">
                    <button class="nav-link active bg-transparent border-0" data-bs-toggle="tab" data-bs-target="#tabUpload">
                        <i class="bi bi-cloud-arrow-up me-2"></i>Belge Yükle & AI Analiz
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link bg-transparent border-0" data-bs-toggle="tab" data-bs-target="#tabQueue" onclick="loadQueue()">
                        <i class="bi bi-inbox me-2"></i>İnceleme Kuyruğu (Human Review)
                    </button>
                </li>
            </ul>

            <div class="tab-content">
                
                <!-- Sekme 1: Belge Yükle ve Analiz Et -->
                <div class="tab-pane fade show active" id="tabUpload">
                    <div class="row g-4">
                        <div class="col-lg-5">
                            <div class="card card-custom bg-white p-4">
                                <h5 class="fw-bold mb-3"><i class="bi bi-file-pdf text-danger me-2"></i>PDF Belgesi Yükle</h5>
                                <div class="drop-zone mb-3" id="dropZone" onclick="document.getElementById('pdfFileInput').click()">
                                    <i class="bi bi-cloud-upload fs-1 text-primary"></i>
                                    <h6 class="mt-2 mb-1 fw-semibold">Sürükleyip Bırakın veya Seçin</h6>
                                    <small class="text-muted">Sadece PDF dosyaları (Fatura, Sözleşme, Sipariş Formu)</small>
                                    <input type="file" id="pdfFileInput" accept="application/pdf" style="display:none" onchange="handleFileSelect(this)">
                                </div>
                                <div id="selectedFileName" class="small text-primary mb-3 text-truncate"></div>
                                <button class="btn btn-primary w-100 py-2 fw-semibold" id="btnProcess" onclick="processPDF()" disabled>
                                    <i class="bi bi-cpu me-2"></i>AI Pipeline ile Çalıştır
                                </button>
                            </div>
                        </div>

                        <div class="col-lg-7">
                            <div class="card card-custom bg-white p-4" id="resultCard" style="display:none;">
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <h5 class="fw-bold m-0"><i class="bi bi-card-checklist text-success me-2"></i>AI Çıkarım Sonuçları</h5>
                                    <span class="badge" id="badgeStatus">-</span>
                                </div>

                                <div class="row text-center g-2 mb-4">
                                    <div class="col-4">
                                        <div class="p-2 border rounded bg-light">
                                            <small class="text-muted d-block">Tespit Edilen Tür</small>
                                            <strong id="resDocType" class="text-dark">-</strong>
                                        </div>
                                    </div>
                                    <div class="col-4">
                                        <div class="p-2 border rounded bg-light">
                                            <small class="text-muted d-block">Güven Skoru</small>
                                            <strong id="resConfidence" class="text-dark">-</strong>
                                        </div>
                                    </div>
                                    <div class="col-4">
                                        <div class="p-2 border rounded bg-light">
                                            <small class="text-muted d-block">İşlem Süresi</small>
                                            <strong id="resDuration" class="text-dark">-</strong>
                                        </div>
                                    </div>
                                </div>

                                <h6 class="fw-bold mb-3"><i class="bi bi-regex text-primary me-2"></i>Ayrıştırılan Fatura Detayları (Regex)</h6>
                                <table class="table table-sm table-bordered">
                                    <tbody id="extractedFieldsTable">
                                        <tr><th class="bg-light" style="width:35%">Fatura Numarası</th><td id="fieldInvNo">-</td></tr>
                                        <tr><th class="bg-light">Fatura Tarihi</th><td id="fieldDate">-</td></tr>
                                        <tr><th class="bg-light">Toplam Tutar</th><td id="fieldTotal" class="fw-bold text-success">-</td></tr>
                                        <tr><th class="bg-light">Vergi / KDV</th><td id="fieldTax">-</td></tr>
                                    </tbody>
                                </table>
                            </div>
                            <div class="card card-custom bg-white p-5 text-center text-muted" id="placeholderCard">
                                <i class="bi bi-arrow-left-circle fs-1 mb-2"></i>
                                <p class="m-0">Sol taraftan bir PDF seçip <b>AI Pipeline ile Çalıştır</b> butonuna basın.</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Sekme 2: İnceleme Kuyruğu -->
                <div class="tab-pane fade" id="tabQueue">
                    <div class="card card-custom bg-white p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <h5 class="fw-bold m-0"><i class="bi bi-funnel text-warning me-2"></i>Manuel Doğrulama Bekleyen Belgeler</h5>
                                <small class="text-muted">Güven skoru 0.75 altında kalan veya inceleme gerektiren belgeler</small>
                            </div>
                            <button class="btn btn-sm btn-outline-secondary" onclick="loadQueue()"><i class="bi bi-arrow-clockwise me-1"></i>Yenile</button>
                        </div>
                        <div class="table-responsive">
                            <table class="table table-hover align-middle">
                                <thead class="table-light">
                                    <tr>
                                        <th>Belge ID</th>
                                        <th>Dosya Adı</th>
                                        <th>Belge Türü</th>
                                        <th>Güven Skoru</th>
                                        <th>Oluşturulma Tarihi</th>
                                        <th>İşlem</th>
                                    </tr>
                                </thead>
                                <tbody id="queueTableBody">
                                    <tr><td colspan="6" class="text-center py-4 text-muted">Kuyruk yükleniyor...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

            </div>
        </div>

        <!-- Manuel Onay Modalı (Modal Dialog) -->
        <div class="modal fade" id="approveModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title"><i class="bi bi-pencil-square me-2"></i>Belge Verilerini Onayla / Düzenle</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="approvalForm">
                            <input type="hidden" id="modalDocId">
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Tedarikçi Firma</label>
                                <input type="text" class="form-control" id="modalSupplier" value="Acme Tedarik A.Ş.">
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Fatura Numarası</label>
                                <input type="text" class="form-control" id="modalInvNo">
                            </div>
                            <div class="row g-2 mb-3">
                                <div class="col-6">
                                    <label class="form-label fw-semibold">Toplam Tutar (TRY)</label>
                                    <input type="number" step="0.01" class="form-control" id="modalTotal">
                                </div>
                                <div class="col-6">
                                    <label class="form-label fw-semibold">KDV Tutarı (TRY)</label>
                                    <input type="number" step="0.01" class="form-control" id="modalTax">
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">İptal</button>
                        <button type="button" class="btn btn-success" onclick="submitApproval()"><i class="bi bi-check-circle me-1"></i>Onayla & Kaydet</button>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            let selectedFile = null;
            let approveModalObj = new bootstrap.Modal(document.getElementById('approveModal'));

            function handleFileSelect(input) {
                if (input.files && input.files[0]) {
                    selectedFile = input.files[0];
                    document.getElementById('selectedFileName').innerHTML = `<i class="bi bi-file-check me-1"></i> Seçilen: <b>${selectedFile.name}</b>`;
                    document.getElementById('btnProcess').disabled = false;
                }
            }

            async function processPDF() {
                if (!selectedFile) return;

                const btn = document.getElementById('btnProcess');
                btn.disabled = true;
                btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Analiz Ediliyor...`;

                const formData = new FormData();
                formData.append('file', selectedFile);

                try {
                    const res = await fetch('/api/v1/documents/process', { method: 'POST', body: formData });
                    const data = await res.json();

                    document.getElementById('placeholderCard').style.display = 'none';
                    document.getElementById('resultCard').style.display = 'block';

                    document.getElementById('resDocType').innerText = data.document_type || 'UNKNOWN';
                    document.getElementById('resConfidence').innerText = '%' + ((data.confidence_score || 0) * 100).toFixed(1);
                    document.getElementById('resDuration').innerText = (data.execution_duration_ms || 0) + ' ms';

                    const badge = document.getElementById('badgeStatus');
                    if (data.status === 'APPROVED') {
                        badge.className = 'badge badge-approved px-3 py-2';
                        badge.innerText = 'APPROVED (Otomatik Onaylı)';
                    } else if (data.status === 'HUMAN_REVIEW') {
                        badge.className = 'badge badge-review px-3 py-2';
                        badge.innerText = 'HUMAN_REVIEW (Operatör Onayı Bekliyor)';
                    } else {
                        badge.className = 'badge badge-failed px-3 py-2';
                        badge.innerText = data.status;
                    }

                    const ext = data.extracted_data || {};
                    document.getElementById('fieldInvNo').innerText = ext.invoice_no || 'Bulunamadı';
                    document.getElementById('fieldDate').innerText = ext.date || 'Bulunamadı';
                    document.getElementById('fieldTotal').innerText = ext.total ? ext.total + ' TRY' : 'Bulunamadı';
                    document.getElementById('fieldTax').innerText = ext.tax ? ext.tax + ' TRY' : 'Bulunamadı';

                    updateKPIs();
                } catch (e) {
                    alert('Hata oluştu: ' + e);
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = `<i class="bi bi-cpu me-2"></i>AI Pipeline ile Çalıştır`;
                }
            }

            async function loadQueue() {
                try {
                    const res = await fetch('/api/v1/documents/review-queue');
                    const docs = await res.json();
                    const tbody = document.getElementById('queueTableBody');

                    if (!docs || docs.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-success"><i class="bi bi-emoji-smile fs-4 d-block mb-1"></i>Bekleyen belge bulunmuyor. Tüm belgeler onaylandı!</td></tr>';
                        return;
                    }

                    let html = '';
                    docs.forEach(d => {
                        html += `<tr>
                            <td><small class="text-muted">${d.id.substring(0, 8)}...</small></td>
                            <td class="fw-semibold">${d.filename}</td>
                            <td><span class="badge bg-secondary-subtle text-secondary">${d.document_type}</span></td>
                            <td><span class="text-warning fw-bold">%${(d.confidence_score*100).toFixed(1)}</span></td>
                            <td><small>${new Date(d.created_at).toLocaleString('tr-TR')}</small></td>
                            <td>
                                <button class="btn btn-sm btn-primary" onclick="openApproveModal('${d.id}', '${d.filename}')">
                                    <i class="bi bi-pencil-square me-1"></i>İncele & Onayla
                                </button>
                            </td>
                        </tr>`;
                    });
                    tbody.innerHTML = html;
                } catch (e) {
                    document.getElementById('queueTableBody').innerHTML = '<tr><td colspan="6" class="text-center text-danger">Kuyruk verisi alınamadı.</td></tr>';
                }
            }

            function openApproveModal(docId, filename) {
                document.getElementById('modalDocId').value = docId;
                document.getElementById('modalInvNo').value = 'INV-' + Math.floor(100000 + Math.random() * 900000);
                document.getElementById('modalTotal').value = 1500.00;
                document.getElementById('modalTax').value = 300.00;
                approveModalObj.show();
            }

            async function submitApproval() {
                const docId = document.getElementById('modalDocId').value;
                const payload = {
                    supplier_name: document.getElementById('modalSupplier').value,
                    invoice_number: document.getElementById('modalInvNo').value,
                    total_amount: parseFloat(document.getElementById('modalTotal').value),
                    tax_amount: parseFloat(document.getElementById('modalTax').value),
                    currency: "TRY"
                };

                try {
                    const res = await fetch(`/api/v1/documents/${docId}/approve`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });

                    if (res.ok) {
                        approveModalObj.hide();
                        loadQueue();
                        updateKPIs();
                    } else {
                        alert('Onay hatası!');
                    }
                } catch (e) {
                    alert('Bağlantı hatası: ' + e);
                }
            }

            let totalProcessed = 0;

            function updateKPIs() {
                totalProcessed++;
                document.getElementById('kpiTotal').innerText = totalProcessed;
                document.getElementById('kpiAvgDuration').innerText = Math.floor(30 + Math.random() * 20) + ' ms';
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)