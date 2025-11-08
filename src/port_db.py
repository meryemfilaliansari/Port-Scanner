"""
Base de données des ports connus et leurs services associés
"""

COMMON_PORTS = {
    20: "FTP Data",
    21: "FTP Control",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    465: "SMTPS",
    587: "SMTP (Submission)",
    993: "IMAPS",
    995: "POP3S",
    1433: "MS SQL Server",
    1521: "Oracle DB",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    6379: "Redis",
    8080: "HTTP Proxy",
    8443: "HTTPS Alt",
    9200: "Elasticsearch",
    27017: "MongoDB"
}

DANGEROUS_PORTS = {
    23: "Telnet - Non sécurisé",
    445: "SMB - Risque WannaCry",
    3389: "RDP - Cible d'attaques",
    5900: "VNC - Souvent mal configuré"
}

PORT_RANGES = {
    "well-known": (0, 1023),
    "registered": (1024, 49151),
    "dynamic": (49152, 65535)
}

def get_port_info(port):
    """
    Retourne les informations sur un port donné
    """
    service = COMMON_PORTS.get(port, "Unknown")
    is_dangerous = port in DANGEROUS_PORTS
    danger_info = DANGEROUS_PORTS.get(port, "") if is_dangerous else ""
    
    # Déterminer la catégorie du port
    category = "dynamic"
    for cat, (start, end) in PORT_RANGES.items():
        if start <= port <= end:
            category = cat
            break
    
    return {
        "port": port,
        "service": service,
        "category": category,
        "is_dangerous": is_dangerous,
        "danger_info": danger_info
    }

def get_common_ports_list():
    """
    Retourne la liste des ports communs à scanner
    """
    return sorted(COMMON_PORTS.keys())