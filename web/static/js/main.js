// État global de l'application
const state = {
    target: null,
    resolvedIp: null,
    selectedProfile: 'quick',
    customPorts: false,
    scanning: false,
    scanId: null,
    results: null,
    profiles: {},
    reconnecting: false
};

// Initialisation Socket.IO avec reconnexion automatique
const socket = io({
    transports: ['websocket', 'polling'],
    upgrade: true,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 10,
    timeout: 20000
});

// Éléments DOM
const elements = {
    target: document.getElementById('target'),
    validationStatus: document.getElementById('validation-status'),
    targetInfo: document.getElementById('target-info'),
    profilesGrid: document.getElementById('profiles-grid'),
    customPortsToggle: document.getElementById('custom-ports-toggle'),
    customPorts: document.getElementById('custom-ports'),
    startScan: document.getElementById('start-scan'),
    stopScan: document.getElementById('stop-scan'),
    progressSection: document.getElementById('progress-section'),
    resultsSection: document.getElementById('results-section'),
    scanTarget: document.getElementById('scan-target'),
    scanPorts: document.getElementById('scan-ports'),
    scanPercentage: document.getElementById('scan-percentage'),
    progressFill: document.getElementById('progress-fill'),
    scanStatus: document.getElementById('scan-status'),
    exportResults: document.getElementById('export-results')
};

console.log('[APP] Application initialisée');

// Charger les profils
async function loadProfiles() {
    try {
        const response = await fetch('/api/profiles');
        state.profiles = await response.json();
        renderProfiles();
        console.log('[APP] Profils chargés:', Object.keys(state.profiles).length);
    } catch (error) {
        console.error('[ERREUR] Chargement des profils:', error);
    }
}

// Afficher les profils
function renderProfiles() {
    elements.profilesGrid.innerHTML = '';
    
    Object.entries(state.profiles).forEach(([key, profile]) => {
        const card = document.createElement('div');
        card.className = 'profile-card';
        card.dataset.profile = key;
        
        if (key === state.selectedProfile) {
            card.classList.add('active');
        }
        
        card.innerHTML = `
            <h3>${profile.name}</h3>
            <p>${profile.description}</p>
            <div class="profile-stats">
                ${profile.ports_count.toLocaleString()} ports | ${profile.threads} threads
            </div>
        `;
        
        card.addEventListener('click', () => selectProfile(key, card));
        elements.profilesGrid.appendChild(card);
    });
}

// Sélectionner un profil
function selectProfile(profileKey, cardElement) {
    state.selectedProfile = profileKey;
    document.querySelectorAll('.profile-card').forEach(card => {
        card.classList.remove('active');
    });
    cardElement.classList.add('active');
    console.log('[APP] Profil sélectionné:', profileKey);
}

// Valider la cible
let validationTimeout;
elements.target.addEventListener('input', (e) => {
    clearTimeout(validationTimeout);
    const target = e.target.value.trim();
    
    if (!target) {
        elements.validationStatus.textContent = '';
        elements.targetInfo.textContent = '';
        elements.startScan.disabled = true;
        return;
    }
    
    elements.validationStatus.textContent = 'Validation...';
    elements.validationStatus.className = 'validation-status';
    
    validationTimeout = setTimeout(async () => {
        try {
            const response = await fetch('/api/validate-target', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target })
            });
            
            const data = await response.json();
            
            if (data.valid) {
                elements.validationStatus.textContent = 'Valide';
                elements.validationStatus.className = 'validation-status valid';
                elements.targetInfo.textContent = data.message || '';
                elements.startScan.disabled = false;
                state.target = data.target;
                state.resolvedIp = data.resolved_ip;
            } else {
                elements.validationStatus.textContent = 'Invalide';
                elements.validationStatus.className = 'validation-status invalid';
                elements.targetInfo.textContent = data.message || '';
                elements.startScan.disabled = true;
            }
        } catch (error) {
            console.error('[ERREUR] Validation:', error);
            elements.validationStatus.textContent = 'Erreur';
            elements.validationStatus.className = 'validation-status invalid';
            elements.startScan.disabled = true;
        }
    }, 500);
});

// Toggle ports personnalisés
elements.customPortsToggle.addEventListener('change', (e) => {
    state.customPorts = e.target.checked;
    elements.customPorts.disabled = !e.target.checked;
    
    const opacity = e.target.checked ? '0.5' : '1';
    const pointerEvents = e.target.checked ? 'none' : 'auto';
    
    document.querySelectorAll('.profile-card').forEach(card => {
        card.style.opacity = opacity;
        card.style.pointerEvents = pointerEvents;
    });
});

// Démarrer le scan
elements.startScan.addEventListener('click', () => {
    if (!state.target) {
        alert('Veuillez entrer une cible valide');
        return;
    }
    
    if (!socket.connected) {
        alert('Connexion WebSocket perdue. Rechargez la page.');
        return;
    }
    
    state.scanId = `scan_${Date.now()}`;
    state.scanning = true;
    
    console.log('[SCAN] Démarrage:', state.scanId);
    
    // Afficher la progression
    elements.progressSection.style.display = 'block';
    elements.resultsSection.style.display = 'none';
    elements.startScan.style.display = 'none';
    elements.stopScan.style.display = 'inline-block';
    
    // Réinitialiser la barre
    elements.scanTarget.textContent = state.resolvedIp || state.target;
    elements.scanPorts.textContent = '...';
    elements.scanPercentage.textContent = '0%';
    elements.progressFill.style.width = '0%';
    elements.scanStatus.textContent = 'Initialisation...';
    
    // Configuration
    const config = {
        scan_id: state.scanId,
        target: state.target,
        profile: state.selectedProfile
    };
    
    if (state.customPorts) {
        config.custom_ports = elements.customPorts.value;
    }
    
    console.log('[SCAN] Configuration:', config);
    socket.emit('start_scan', config);
});

// Arrêter le scan
elements.stopScan.addEventListener('click', () => {
    if (state.scanId) {
        socket.emit('stop_scan', { scan_id: state.scanId });
        resetUI();
    }
});

// Réinitialiser l'UI
function resetUI() {
    state.scanning = false;
    elements.progressSection.style.display = 'none';
    elements.startScan.style.display = 'inline-block';
    elements.stopScan.style.display = 'none';
}

// Socket.IO Events
socket.on('connect', () => {
    console.log('[WEBSOCKET] Connecté');
    state.reconnecting = false;
    
    // Si un scan était en cours, notifier l'utilisateur
    if (state.scanning) {
        elements.scanStatus.textContent = 'Connexion rétablie...';
    }
});

socket.on('disconnect', (reason) => {
    console.warn('[WEBSOCKET] Déconnecté:', reason);
    state.reconnecting = true;
    
    if (state.scanning) {
        elements.scanStatus.textContent = 'Connexion perdue, reconnexion...';
    }
});

socket.on('reconnect', (attemptNumber) => {
    console.log('[WEBSOCKET] Reconnecté après', attemptNumber, 'tentatives');
    state.reconnecting = false;
});

socket.on('reconnect_error', (error) => {
    console.error('[WEBSOCKET] Erreur de reconnexion:', error);
});

socket.on('scan_started', (data) => {
    console.log('[SCAN] Démarré:', data.scan_id);
    
    if (data.scan_id === state.scanId) {
        elements.scanPorts.textContent = data.ports_count.toLocaleString();
        elements.scanStatus.textContent = 'Scan en cours...';
        elements.progressFill.style.width = '1%';
    }
});

socket.on('scan_progress', (data) => {
    if (data.scan_id === state.scanId) {
        const percentage = Math.round(data.percentage);
        elements.scanPercentage.textContent = `${percentage}%`;
        elements.progressFill.style.width = `${percentage}%`;
        elements.scanStatus.textContent = `${data.progress.toLocaleString()} / ${data.total.toLocaleString()} ports`;
        console.log('[SCAN] Progression:', percentage + '%');
    }
});

socket.on('scan_complete', (data) => {
    console.log('[SCAN] Terminé:', data.scan_id);
    
    if (data.scan_id !== state.scanId) {
        console.warn('[SCAN] ID ne correspond pas, ignoré');
        return;
    }
    
    state.scanning = false;
    state.results = data.results;
    
    // Animation finale
    elements.progressFill.style.width = '100%';
    elements.scanPercentage.textContent = '100%';
    elements.scanStatus.textContent = 'Scan terminé !';
    
    // Afficher les résultats après animation
    setTimeout(() => {
        elements.progressSection.style.display = 'none';
        elements.resultsSection.style.display = 'block';
        elements.startScan.style.display = 'inline-block';
        elements.stopScan.style.display = 'none';
        
        displayResults(data.results);
    }, 800);
});

socket.on('scan_error', (data) => {
    console.error('[ERREUR] Scan:', data.error);
    alert(`Erreur durant le scan: ${data.error}`);
    resetUI();
});

socket.on('scan_stopped', (data) => {
    console.log('[SCAN] Arrêté:', data.scan_id);
    alert('Scan arrêté');
    resetUI();
});

// Afficher les résultats
function displayResults(results) {
    console.log('[AFFICHAGE] Résultats:', results.open_ports.length, 'ports ouverts');
    
    // Statistiques
    document.getElementById('stat-total').textContent = results.total_ports.toLocaleString();
    document.getElementById('stat-open').textContent = results.open_ports.length.toLocaleString();
    document.getElementById('stat-closed').textContent = results.closed_ports.toLocaleString();
    document.getElementById('stat-filtered').textContent = results.filtered_ports.toLocaleString();
    
    // Détails
    document.getElementById('scan-duration').textContent = formatDuration(results.duration);
    document.getElementById('scan-speed').textContent = `${Math.round(results.scan_speed)} ports/s`;
    document.getElementById('scan-time').textContent = new Date(results.end_time).toLocaleString('fr-FR');
    
    // Table des ports
    const tbody = document.getElementById('ports-tbody');
    tbody.innerHTML = '';
    
    if (results.open_ports.length === 0) {
        document.getElementById('no-ports-message').style.display = 'block';
        document.getElementById('ports-table-container').style.display = 'none';
    } else {
        document.getElementById('no-ports-message').style.display = 'none';
        document.getElementById('ports-table-container').style.display = 'block';
        
        results.open_ports.forEach(port => {
            const tr = document.createElement('tr');
            
            const statusBadge = port.is_dangerous
                ? '<span class="badge badge-danger">Attention</span>'
                : '<span class="badge badge-safe">OK</span>';
            
            let banner = 'N/A';
            if (port.banner) {
                const shortBanner = port.banner.substring(0, 60);
                banner = `<span class="banner-text" title="${escapeHtml(port.banner)}">${escapeHtml(shortBanner)}${port.banner.length > 60 ? '...' : ''}</span>`;
            } else {
                banner = '<span style="color: #9ca3af;">N/A</span>';
            }
            
            tr.innerHTML = `
                <td><span class="port-number">${port.port}</span></td>
                <td>${port.service}</td>
                <td>${port.category}</td>
                <td>${statusBadge}</td>
                <td>${banner}</td>
            `;
            
            tbody.appendChild(tr);
        });
    }
    
    // Avertissements
    const dangerousPorts = results.open_ports.filter(p => p.is_dangerous);
    
    if (dangerousPorts.length > 0) {
        document.getElementById('warnings-section').style.display = 'block';
        const warningsContainer = document.getElementById('warnings-container');
        warningsContainer.innerHTML = '';
        
        dangerousPorts.forEach(port => {
            const warning = document.createElement('div');
            warning.className = 'warning-card danger';
            warning.innerHTML = `
                <h4>Port ${port.port} - ${port.service}</h4>
                <p>${port.danger_info}</p>
            `;
            warningsContainer.appendChild(warning);
        });
    } else {
        document.getElementById('warnings-section').style.display = 'none';
    }
    
    console.log('[AFFICHAGE] Terminé');
}

// Exporter les résultats
elements.exportResults.addEventListener('click', () => {
    if (!state.results) {
        alert('Aucun résultat à exporter');
        return;
    }
    
    const dataStr = JSON.stringify(state.results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `scan_${state.results.target}_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    
    URL.revokeObjectURL(url);
    console.log('[EXPORT] Fichier téléchargé');
});

// Utilitaires
function formatDuration(seconds) {
    if (seconds < 60) {
        return `${seconds.toFixed(2)} s`;
    } else if (seconds < 3600) {
        return `${(seconds / 60).toFixed(2)} min`;
    } else {
        return `${(seconds / 3600).toFixed(2)} h`;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    console.log('[APP] DOM chargé');
    loadProfiles();
    
    // Vérifier la connexion après 2 secondes
    setTimeout(() => {
        if (!socket.connected) {
            console.error('[WEBSOCKET] Pas de connexion !');
            alert('Erreur de connexion WebSocket. Rechargez la page.');
        } else {
            console.log('[WEBSOCKET] ✓ Connexion OK');
        }
    }, 2000);
});