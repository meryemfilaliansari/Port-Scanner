#!/usr/bin/env python3
"""
Scanner de Ports Automatique
Point d'entrée principal du programme
"""
import sys
import argparse
import yaml
from pathlib import Path

# Ajouter le dossier src au path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from scanner import PortScanner
from reporter import Reporter
from port_db import get_common_ports_list, get_port_info
from utils import (
    validate_ip, 
    resolve_hostname, 
    validate_port_range,
    print_banner,
    print_success,
    print_error,
    print_warning,
    print_info,
    format_scan_time
)

def load_config(config_file='config/config.yaml'):
    """
    Charge le fichier de configuration
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print_warning(f"Fichier de configuration non trouvé: {config_file}")
        return None
    except Exception as e:
        print_error(f"Erreur lors du chargement de la config: {e}")
        return None

def parse_arguments():
    """
    Parse les arguments de la ligne de commande
    """
    parser = argparse.ArgumentParser(
        description='Scanner de Ports Automatique',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python main.py -t 192.168.1.1                    # Scan rapide
  python main.py -t example.com -p 1-1000          # Scan des ports 1-1000
  python main.py -t 192.168.1.1 -p 80,443,8080     # Scan de ports spécifiques
  python main.py -t 192.168.1.1 --profile full     # Scan complet
  python main.py -t 192.168.1.1 --profile web      # Scan des ports web
        """
    )
    
    parser.add_argument('-t', '--target', 
                       required=True,
                       help='Adresse IP ou nom d\'hôte cible')
    
    parser.add_argument('-p', '--ports',
                       help='Ports à scanner (ex: 80,443,8000-9000 ou "common" pour les ports communs)')
    
    parser.add_argument('--profile',
                       choices=['quick', 'full', 'web', 'database', 'safe'],
                       help='Profil de scan prédéfini')
    
    parser.add_argument('--threads',
                       type=int,
                       help='Nombre de threads (défaut: 100)')
    
    parser.add_argument('--timeout',
                       type=float,
                       help='Timeout en secondes (défaut: 1)')
    
    parser.add_argument('-o', '--output',
                       help='Nom du fichier de sortie (sans extension)')
    
    parser.add_argument('--no-report',
                       action='store_true',
                       help='Ne pas générer de rapports')
    
    parser.add_argument('--json-only',
                       action='store_true',
                       help='Générer uniquement le rapport JSON')
    
    parser.add_argument('--html-only',
                       action='store_true',
                       help='Générer uniquement le rapport HTML')
    
    parser.add_argument('-v', '--verbose',
                       action='store_true',
                       help='Mode verbose')
    
    return parser.parse_args()

def main():
    """
    Fonction principale
    """
    print_banner()
    
    # Parser les arguments
    args = parse_arguments()
    
    # Charger la configuration
    config = load_config()
    
    # Valider la cible
    print_info(f"Validation de la cible: {args.target}")
    
    if not validate_ip(args.target):
        print_error(f"Cible invalide: {args.target}")
        sys.exit(1)
    
    # Résoudre le nom d'hôte si nécessaire
    target_ip = resolve_hostname(args.target)
    if target_ip:
        print_success(f"Cible résolue: {args.target} -> {target_ip}")
        target = target_ip
    else:
        target = args.target
    
    # Déterminer les ports à scanner
    ports = []
    
    if args.profile and config:
        # Utiliser un profil prédéfini
        profile = config['scan_profiles'].get(args.profile)
        if profile:
            print_info(f"Utilisation du profil: {args.profile} - {profile['description']}")
            
            if profile['ports'] == 'common':
                ports = get_common_ports_list()
            else:
                ports = validate_port_range(profile['ports'])
            
            threads = args.threads or profile.get('threads', 100)
            timeout = args.timeout or profile.get('timeout', 1)
        else:
            print_error(f"Profil non trouvé: {args.profile}")
            sys.exit(1)
    elif args.ports:
        # Utiliser les ports spécifiés
        if args.ports.lower() == 'common':
            ports = get_common_ports_list()
            print_info(f"Scan des {len(ports)} ports communs")
        else:
            ports = validate_port_range(args.ports)
            if not ports:
                print_error("Ports invalides")
                sys.exit(1)
        
        threads = args.threads or (config['scan']['threads'] if config else 100)
        timeout = args.timeout or (config['scan']['timeout'] if config else 1)
    else:
        # Scan rapide par défaut
        ports = get_common_ports_list()
        threads = args.threads or 200
        timeout = args.timeout or 0.5
        print_info("Aucun port spécifié, scan rapide des ports communs")
    
    if not ports:
        print_error("Aucun port à scanner")
        sys.exit(1)
    
    print_info(f"Configuration: {len(ports)} ports, {threads} threads, timeout {timeout}s")
    
    # Créer le scanner
    scanner = PortScanner(
        target=target,
        ports=ports,
        timeout=timeout,
        threads=threads
    )
    
    # Lancer le scan
    try:
        print_success("Démarrage du scan...")
        results = scanner.scan(verbose=args.verbose)
        
        print_success(f"Scan terminé en {format_scan_time(results['duration'])}")
        print_success(f"Ports ouverts trouvés: {len(results['open_ports'])}")
        
        # Générer les rapports
        if not args.no_report:
            reporter = Reporter(results)
            
            # Rapport console (toujours affiché sauf si --json-only ou --html-only)
            if not (args.json_only or args.html_only):
                reporter.print_console_report()
            
            # Rapports fichiers
            if not args.json_only and not args.html_only:
                # Les deux formats
                reporter.generate_json_report(args.output + '.json' if args.output else None)
                reporter.generate_html_report(args.output + '.html' if args.output else None)
            elif args.json_only:
                reporter.generate_json_report(args.output + '.json' if args.output else None)
            elif args.html_only:
                reporter.generate_html_report(args.output + '.html' if args.output else None)
        
        # Afficher des avertissements si des ports dangereux sont ouverts
        dangerous_found = [p for p in results['open_ports'] 
                          if get_port_info(p['port'])['is_dangerous']]
        
        if dangerous_found:
            print_warning(f"\nATTENTION: {len(dangerous_found)} port(s) potentiellement dangereux détecté(s)!")
            for port_data in dangerous_found:
                port_info = get_port_info(port_data['port'])
                print_warning(f"  Port {port_data['port']}: {port_info['danger_info']}")
        
    except KeyboardInterrupt:
        print_error("\nScan interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erreur lors du scan: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()