"""
Module de génération de rapports
"""
import json
from datetime import datetime
from colorama import Fore, Style
from port_db import get_port_info

class Reporter:
    def __init__(self, results):
        """
        Initialise le générateur de rapports
        
        Args:
            results: Dictionnaire des résultats du scan
        """
        self.results = results
    
    def print_console_report(self):
        """
        Affiche le rapport dans la console
        """
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"                    RÉSULTATS DU SCAN")
        print(f"{'='*70}{Style.RESET_ALL}\n")
        
        # Informations générales
        print(f"{Fore.YELLOW}Cible:{Style.RESET_ALL} {self.results['target']}")
        print(f"{Fore.YELLOW}Début du scan:{Style.RESET_ALL} {self.results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.YELLOW}Fin du scan:{Style.RESET_ALL} {self.results['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.YELLOW}Durée:{Style.RESET_ALL} {self.results['duration']:.2f} secondes")
        print(f"{Fore.YELLOW}Vitesse:{Style.RESET_ALL} {self.results['scan_speed']:.2f} ports/seconde\n")
        
        # Statistiques
        print(f"{Fore.CYAN}--- STATISTIQUES ---{Style.RESET_ALL}")
        print(f"Ports scannés: {self.results['total_ports']}")
        print(f"{Fore.GREEN}Ports ouverts: {len(self.results['open_ports'])}{Style.RESET_ALL}")
        print(f"Ports fermés: {self.results['closed_ports']}")
        print(f"Ports filtrés: {self.results['filtered_ports']}\n")
        
        # Liste des ports ouverts
        if self.results['open_ports']:
            print(f"{Fore.CYAN}--- PORTS OUVERTS ---{Style.RESET_ALL}\n")
            print(f"{'PORT':<8} {'SERVICE':<20} {'CATÉGORIE':<15} {'BANNIÈRE'}")
            print("-" * 70)
            
            for port_data in self.results['open_ports']:
                port = port_data['port']
                banner = port_data['banner'][:30] if port_data['banner'] else "N/A"
                info = get_port_info(port)
                
                # Coloration selon le danger
                if info['is_dangerous']:
                    color = Fore.RED
                    warning = " [ATTENTION]"
                else:
                    color = Fore.GREEN
                    warning = ""
                
                print(f"{color}{port:<8} {info['service']:<20} {info['category']:<15} {banner}{warning}{Style.RESET_ALL}")
                
                if info['is_dangerous']:
                    print(f"  {Fore.YELLOW}⚠ {info['danger_info']}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Aucun port ouvert détecté.{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    
    def generate_json_report(self, filename=None):
        """
        Génère un rapport au format JSON
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"results/scan_{self.results['target']}_{timestamp}.json"
        
        # Préparer les données pour JSON
        json_data = {
            'target': self.results['target'],
            'start_time': self.results['start_time'].isoformat(),
            'end_time': self.results['end_time'].isoformat(),
            'duration_seconds': self.results['duration'],
            'statistics': {
                'total_ports_scanned': self.results['total_ports'],
                'open_ports_count': len(self.results['open_ports']),
                'closed_ports_count': self.results['closed_ports'],
                'filtered_ports_count': self.results['filtered_ports'],
                'scan_speed': self.results['scan_speed']
            },
            'open_ports': []
        }
        
        # Ajouter les détails des ports ouverts
        for port_data in self.results['open_ports']:
            port = port_data['port']
            info = get_port_info(port)
            json_data['open_ports'].append({
                'port': port,
                'service': info['service'],
                'category': info['category'],
                'is_dangerous': info['is_dangerous'],
                'danger_info': info['danger_info'],
                'banner': port_data['banner']
            })
        
        # Écrire le fichier JSON
        try:
            import os
            os.makedirs('results', exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"{Fore.GREEN}[+] Rapport JSON sauvegardé: {filename}{Style.RESET_ALL}")
            return filename
        except Exception as e:
            print(f"{Fore.RED}[-] Erreur lors de la sauvegarde: {e}{Style.RESET_ALL}")
            return None
    
    def generate_html_report(self, filename=None):
        """
        Génère un rapport au format HTML
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"results/scan_{self.results['target']}_{timestamp}.html"
        
        html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport de Scan - {self.results['target']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f4f4f4; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        .info {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-box {{ background: #3498db; color: white; padding: 15px; border-radius: 5px; text-align: center; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #2c3e50; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f5f5f5; }}
        .dangerous {{ background: #e74c3c; color: white; padding: 2px 8px; border-radius: 3px; }}
        .safe {{ background: #27ae60; color: white; padding: 2px 8px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Rapport de Scan de Ports</h1>
        
        <div class="info">
            <p><strong>Cible:</strong> {self.results['target']}</p>
            <p><strong>Date:</strong> {self.results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Durée:</strong> {self.results['duration']:.2f} secondes</p>
        </div>
        
        <h2>Statistiques</h2>
        <div class="stats">
            <div class="stat-box">
                <h3>{self.results['total_ports']}</h3>
                <p>Ports Scannés</p>
            </div>
            <div class="stat-box" style="background: #27ae60;">
                <h3>{len(self.results['open_ports'])}</h3>
                <p>Ports Ouverts</p>
            </div>
            <div class="stat-box" style="background: #95a5a6;">
                <h3>{self.results['closed_ports']}</h3>
                <p>Ports Fermés</p>
            </div>
            <div class="stat-box" style="background: #e67e22;">
                <h3>{self.results['filtered_ports']}</h3>
                <p>Ports Filtrés</p>
            </div>
        </div>
        
        <h2>Ports Ouverts</h2>
        <table>
            <thead>
                <tr>
                    <th>Port</th>
                    <th>Service</th>
                    <th>Catégorie</th>
                    <th>Statut</th>
                    <th>Bannière</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for port_data in self.results['open_ports']:
            port = port_data['port']
            info = get_port_info(port)
            banner = port_data['banner'][:50] if port_data['banner'] else "N/A"
            status_class = "dangerous" if info['is_dangerous'] else "safe"
            status_text = "ATTENTION" if info['is_dangerous'] else "OK"
            
            html_content += f"""
                <tr>
                    <td><strong>{port}</strong></td>
                    <td>{info['service']}</td>
                    <td>{info['category']}</td>
                    <td><span class="{status_class}">{status_text}</span></td>
                    <td>{banner}</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        
        try:
            import os
            os.makedirs('results', exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"{Fore.GREEN}[+] Rapport HTML sauvegardé: {filename}{Style.RESET_ALL}")
            return filename
        except Exception as e:
            print(f"{Fore.RED}[-] Erreur lors de la sauvegarde: {e}{Style.RESET_ALL}")
            return None