"""
Fonctions utilitaires pour le scanner de ports
"""
import socket
import ipaddress
import re
from colorama import Fore, Style, init

# Initialiser colorama
init(autoreset=True)

def validate_ip(ip_string):
    """
    Valide une adresse IP ou un nom d'hôte
    """
    try:
        # Essayer de résoudre comme nom d'hôte
        socket.gethostbyname(ip_string)
        return True
    except socket.gaierror:
        return False

def resolve_hostname(target):
    """
    Résout un nom d'hôte en adresse IP
    """
    try:
        return socket.gethostbyname(target)
    except socket.gaierror:
        return None

def validate_port_range(port_range_str):
    """
    Valide et parse une chaîne de ports (ex: "80,443,8000-9000")
    Retourne une liste de ports
    """
    ports = set()
    
    try:
        parts = port_range_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Range de ports
                start, end = map(int, part.split('-'))
                if start > end or start < 1 or end > 65535:
                    raise ValueError("Port range invalide")
                ports.update(range(start, end + 1))
            else:
                # Port unique
                port = int(part)
                if port < 1 or port > 65535:
                    raise ValueError("Port invalide")
                ports.add(port)
        return sorted(list(ports))
    except Exception as e:
        print(f"{Fore.RED}Erreur de validation: {e}")
        return None

def print_banner():
    """
    Affiche la bannière du programme
    """
    banner = f"""
{Fore.CYAN}{'='*60}
{Fore.CYAN}           SCANNER DE PORTS AUTOMATIQUE
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
"""
    print(banner)

def print_success(message):
    """Affiche un message de succès"""
    print(f"{Fore.GREEN}[+] {message}{Style.RESET_ALL}")

def print_error(message):
    """Affiche un message d'erreur"""
    print(f"{Fore.RED}[-] {message}{Style.RESET_ALL}")

def print_warning(message):
    """Affiche un avertissement"""
    print(f"{Fore.YELLOW}[!] {message}{Style.RESET_ALL}")

def print_info(message):
    """Affiche une information"""
    print(f"{Fore.BLUE}[*] {message}{Style.RESET_ALL}")

def format_scan_time(seconds):
    """
    Formate le temps de scan en format lisible
    """
    if seconds < 60:
        return f"{seconds:.2f} secondes"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.2f} heures"