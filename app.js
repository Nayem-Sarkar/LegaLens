document.addEventListener('DOMContentLoaded', () => {
    // Setup Drag and Drop
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    // Setup Paste Text
    const analyzeTextBtn = document.getElementById('analyze-text-btn');
    const pasteInput = document.getElementById('paste-input');
    
    analyzeTextBtn.addEventListener('click', () => {
        const text = pasteInput.value.trim();
        if (text) {
            handleTextSubmission(text);
        } else {
            alert('Please paste some text first!');
        }
    });
});

async function handleTextSubmission(text) {
    const formData = new FormData();
    formData.append('text', text);
    await sendAnalysisRequest(formData);
}

async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    await sendAnalysisRequest(formData);
}

async function sendAnalysisRequest(formData) {
    const list = document.getElementById('findings-list');
    const dashboard = document.getElementById('dashboard-section');
    const dropZone = document.getElementById('drop-zone');
    const pasteZone = document.getElementById('paste-zone');
    const loadingState = document.getElementById('loading-indicator');
    
    // UI Transitions
    dropZone.classList.add('hidden');
    pasteZone.classList.add('hidden');
    loadingState.classList.remove('hidden');
    dashboard.style.display = 'none';
    
    list.innerHTML = '';
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error || 'Server rejected file');
        }
        
        const data = await response.json();
        renderDashboard(data);
        
        // Show Dashboard
        dashboard.style.display = 'block';
        loadingState.classList.add('hidden');
        dropZone.classList.remove('hidden');
        pasteZone.classList.remove('hidden');
        
    } catch (err) {
        console.error(err);
        loadingState.classList.add('hidden');
        dropZone.classList.remove('hidden');
        pasteZone.classList.remove('hidden');
        alert("Error analyzing content: " + err.message);
    }
}

function renderDashboard(data) {
    // Top Level Summary Stats
    document.getElementById('doc-name').textContent = data.document || 'Unknown Document';
    
    const overallBadge = document.getElementById('overall-badge');
    const risk = data.overall_risk || 'Green';
    overallBadge.textContent = risk + ' Risk';
    overallBadge.className = `risk-badge ${risk.toLowerCase()}`;
    
    document.getElementById('count-red').textContent = data.summary?.red || 0;
    document.getElementById('count-yellow').textContent = data.summary?.yellow || 0;
    document.getElementById('count-green').textContent = data.summary?.green || 0;
    
    // Findings Iteration
    const list = document.getElementById('findings-list');
    list.innerHTML = '';
    
    if (!data.findings || data.findings.length === 0) {
        list.innerHTML = '<div class="glass-panel" style="padding: 2rem; color: var(--text-muted); grid-column: 1/-1; text-align: center;">No findings detected!</div>';
        return;
    }
    
    // Sort so red is first, then yellow, then green
    const colorOrder = { "Red": 1, "Yellow": 2, "Green": 3 };
    data.findings.sort((a, b) => colorOrder[a.risk_level] - colorOrder[b.risk_level]);

    // Construct cards
    data.findings.forEach((finding, index) => {
        const riskClass = finding.risk_level ? finding.risk_level.toLowerCase().trim() : 'green';
        
        const card = document.createElement('div');
        card.className = `glass-panel finding-card risk-${riskClass}`;
        
        // Stagger entrance animation
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.animation = `fadeSlideIn 0.5s ease forwards ${index * 0.1}s`;
        
        card.innerHTML = `
            <div class="card-header">
                <span class="risk-tag ${riskClass}">${finding.risk_level}</span>
            </div>
            <h3 class="finding-issue">${escapeHtml(finding.issue)}</h3>
            ${finding.evidence ? `<blockquote class="evidence-box">"${escapeHtml(finding.evidence)}"</blockquote>` : ''}
            <div class="fix-suggestion">
                <strong>Recommendation:</strong> ${escapeHtml(finding.fix)}
            </div>
        `;
        
        list.appendChild(card);
    });
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// Add our keyframes to the document via JS so we don't clutter the main CSS
const styleSheet = document.createElement("style");
styleSheet.innerText = `
@keyframes fadeSlideIn {
    to { 
        opacity: 1; 
        transform: translateY(0); 
    }
}
`;
document.head.appendChild(styleSheet);
