#!/usr/bin/env python3
"""
Application Flask pour l'interface web du scanner de ports - VERSION CORRIGÉE
"""
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import sys
from pathlib import Path
from datetime import datetime

# Ajouter le dossier src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from scanner import PortScanner
from port_db import get_common_ports_list, get_port_info
from utils import validate_ip, resolve_hostname, validate_port_range

app = Flask(__name__)
app.config['SECRET_KEY'] = 'scanner-ports-secret-key-2024'
CORS(app)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='eventlet',
    ping_interval=10,  # Ping toutes les 10 secondes
    ping_timeout=120,  # Timeout après 120 secondes
    logger=False,
    engineio_logger=False
)

# Stocker les scans en cours
active_scans = {}

@app.route('/')
def index():
    """Page principale"""
    return render_template('index.html')

@app.route('/api/validate-target', methods=['POST'])
def validate_target():
    """Valide une cible (IP ou hostname)"""
    data = request.get_json()
    target = data.get('target', '')
    
    if not target:
        return jsonify({'valid': False, 'message': 'Cible vide'})
    
    if not validate_ip(target):
        return jsonify({'valid': False, 'message': 'Cible invalide'})
    
    resolved_ip = resolve_hostname(target)
    if resolved_ip:
        return jsonify({
            'valid': True,
            'target': target,
            'resolved_ip': resolved_ip,
            'message': f'Résolu: {target} -> {resolved_ip}'
        })
    
    return jsonify({'valid': True, 'target': target, 'resolved_ip': target})

@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    """Retourne les profils de scan disponibles"""
    profiles = {
        'quick': {
            'name': 'Scan Rapide',
            'description': 'Ports communs uniquement',
            'ports_count': len(get_common_ports_list()),
            'threads': 200,
            'timeout': 0.5
        },
        'web': {
            'name': 'Services Web',
            'description': 'Ports HTTP/HTTPS',
            'ports_count': 6,
            'threads': 50,
            'timeout': 2
        },
        'database': {
            'name': 'Bases de Données',
            'description': 'MySQL, PostgreSQL, MongoDB, Redis',
            'ports_count': 6,
            'threads': 50,
            'timeout': 2
        },
        'full': {
            'name': 'Scan Complet',
            'description': 'Tous les ports (1-65535)',
            'ports_count': 65535,
            'threads': 500,
            'timeout': 0.5
        },
        'safe': {
            'name': 'Scan Discret',
            'description': 'Lent pour éviter la détection',
            'ports_count': len(get_common_ports_list()),
            'threads': 10,
            'timeout': 3
        }
    }
    return jsonify(profiles)

@socketio.on('connect')
def handle_connect():
    """Gestion de la connexion WebSocket"""
    print(f'[WEBSOCKET] Client connecté: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    """Gestion de la déconnexion WebSocket"""
    print(f'[WEBSOCKET] Client déconnecté: {request.sid}')

@socketio.on('start_scan')
def handle_scan(data):
    """Démarre un scan via WebSocket"""
    scan_id = data.get('scan_id')
    target = data.get('target')
    profile = data.get('profile', 'quick')
    custom_ports = data.get('custom_ports', None)
    
    print(f"\n{'='*60}")
    print(f"[SCAN] Nouveau scan: {scan_id}")
    print(f"[SCAN] Cible: {target}")
    print(f"[SCAN] Profil: {profile}")
    print(f"{'='*60}\n")
    
    # Valider la cible
    if not validate_ip(target):
        print(f"[ERREUR] Cible invalide: {target}")
        emit('scan_error', {
            'scan_id': scan_id,
            'error': 'Cible invalide'
        })
        return
    
    # Résoudre le hostname
    resolved_ip = resolve_hostname(target) or target
    print(f"[SCAN] IP résolue: {resolved_ip}")
    
    # Déterminer les ports
    if custom_ports:
        print(f"[SCAN] Ports personnalisés: {custom_ports}")
        ports = validate_port_range(custom_ports)
        if not ports:
            print(f"[ERREUR] Ports invalides")
            emit('scan_error', {
                'scan_id': scan_id,
                'error': 'Ports invalides'
            })
            return
        threads = 100
        timeout = 1
    else:
        # Profils prédéfinis
        profile_config = {
            'quick': {
                'ports': get_common_ports_list(),
                'threads': 200,
                'timeout': 0.5
            },
            'web': {
                'ports': [80, 443, 8000, 8080, 8443, 8888],
                'threads': 50,
                'timeout': 2
            },
            'database': {
                'ports': [1433, 3306, 5432, 27017, 6379, 9200],
                'threads': 50,
                'timeout': 2
            },
            'full': {
                'ports': list(range(1, 65536)),
                'threads': 500,
                'timeout': 0.5
            },
            'safe': {
                'ports': get_common_ports_list(),
                'threads': 10,
                'timeout': 3
            }
        }
        
        config = profile_config.get(profile, profile_config['quick'])
        ports = config['ports']
        threads = config['threads']
        timeout = config['timeout']
    
    print(f"[SCAN] Configuration: {len(ports)} ports, {threads} threads, timeout {timeout}s")
    
    # Émettre le début du scan
    emit('scan_started', {
        'scan_id': scan_id,
        'target': resolved_ip,
        'ports_count': len(ports),
        'start_time': datetime.now().isoformat()
    })
    
    def run_scan():
        """Fonction de scan en arrière-plan"""
        try:
            print(f"[SCAN] Création du scanner...")
            
            # Créer le scanner
            scanner = PortScanner(
                target=resolved_ip,
                ports=ports,
                timeout=timeout,
                threads=threads
            )
            
            print(f"[SCAN] Lancement du scan...")
            
            # Lancer le scan
            results = scanner.scan(verbose=False)
            
            print(f"[SCAN] Scan terminé!")
            print(f"[SCAN] Ports scannés: {results['total_ports']}")
            print(f"[SCAN] Ports ouverts: {len(results['open_ports'])}")
            print(f"[SCAN] Durée: {results['duration']:.2f}s")
            
            # Enrichir les résultats avec les infos des ports
            enriched_ports = []
            for port_data in results['open_ports']:
                port = port_data['port']
                info = get_port_info(port)
                enriched_ports.append({
                    'port': port,
                    'service': info['service'],
                    'category': info['category'],
                    'is_dangerous': info['is_dangerous'],
                    'danger_info': info['danger_info'],
                    'banner': port_data['banner']
                })
                print(f"[SCAN] Port ouvert: {port} ({info['service']})")
            
            results['open_ports'] = enriched_ports
            results['start_time'] = results['start_time'].isoformat()
            results['end_time'] = results['end_time'].isoformat()
            
            print(f"[SCAN] Émission des résultats au client...")
            
            # Émettre les résultats
            socketio.emit('scan_complete', {
                'scan_id': scan_id,
                'results': results
            })
            
            print(f"[SCAN] ✓ Résultats envoyés avec succès!")
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"\n[ERREUR] Exception durant le scan:")
            print(f"[ERREUR] {error_msg}")
            print(traceback.format_exc())
            
            socketio.emit('scan_error', {
                'scan_id': scan_id,
                'error': error_msg
            })
        finally:
            if scan_id in active_scans:
                del active_scans[scan_id]
                print(f"[SCAN] Scan {scan_id} nettoyé\n")
    
    # Lancer le scan dans un thread en arrière-plan
    active_scans[scan_id] = True
    socketio.start_background_task(run_scan)

@socketio.on('stop_scan')
def handle_stop_scan(data):
    """Arrête un scan en cours"""
    scan_id = data.get('scan_id')
    print(f"[SCAN] Arrêt demandé pour {scan_id}")
    
    if scan_id in active_scans:
        del active_scans[scan_id]
        emit('scan_stopped', {'scan_id': scan_id})
        print(f"[SCAN] Scan {scan_id} arrêté")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  SCANNER DE PORTS - INTERFACE WEB")
    print("="*60)
    print("\nDémarrage du serveur...")
    print("Interface accessible sur: http://localhost:5000")
    print("\nAppuyez sur Ctrl+C pour arrêter\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)
