"""
Module principal de scan de ports
"""
import socket
import threading
import time
from datetime import datetime
from tqdm import tqdm
from queue import Queue

class PortScanner:
    def __init__(self, target, ports, timeout=1, threads=100):
        """
        Initialise le scanner de ports
        
        Args:
            target: Adresse IP ou nom d'hôte cible
            ports: Liste des ports à scanner
            timeout: Timeout pour chaque connexion (secondes)
            threads: Nombre de threads pour le scan parallèle
        """
        self.target = target
        self.ports = ports
        self.timeout = timeout
        self.threads = threads
        self.open_ports = []
        self.closed_ports = []
        self.filtered_ports = []
        self.queue = Queue()
        self.lock = threading.Lock()
        self.start_time = None
        self.end_time = None
        
    def scan_port(self, port):
        """
        Scan un port unique
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.target, port))
            
            if result == 0:
                # Port ouvert
                try:
                    # Tenter de récupérer la bannière
                    sock.send(b'Hello\r\n')
                    banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
                except:
                    banner = ""
                
                with self.lock:
                    self.open_ports.append({
                        'port': port,
                        'banner': banner
                    })
            else:
                with self.lock:
                    self.closed_ports.append(port)
            
            sock.close()
            
        except socket.timeout:
            with self.lock:
                self.filtered_ports.append(port)
        except socket.error:
            with self.lock:
                self.filtered_ports.append(port)
        except Exception as e:
            with self.lock:
                self.closed_ports.append(port)
    
    def worker(self, progress_bar):
        """
        Fonction worker pour les threads
        """
        while True:
            port = self.queue.get()
            if port is None:
                break
            
            self.scan_port(port)
            progress_bar.update(1)
            self.queue.task_done()
    
    def scan(self, verbose=True):
        """
        Lance le scan de tous les ports
        """
        self.start_time = datetime.now()
        
        if verbose:
            print(f"\n[*] Démarrage du scan sur {self.target}")
            print(f"[*] Nombre de ports à scanner: {len(self.ports)}")
            print(f"[*] Threads: {self.threads}")
            print(f"[*] Timeout: {self.timeout}s\n")
        
        # Ajouter tous les ports à la queue
        for port in self.ports:
            self.queue.put(port)
        
        # Créer la barre de progression
        progress_bar = tqdm(total=len(self.ports), desc="Scan en cours", unit="port")
        
        # Créer et démarrer les threads
        threads_list = []
        for _ in range(min(self.threads, len(self.ports))):
            thread = threading.Thread(target=self.worker, args=(progress_bar,))
            thread.daemon = True
            thread.start()
            threads_list.append(thread)
        
        # Attendre que tous les ports soient scannés
        self.queue.join()
        
        # Arrêter les threads
        for _ in range(len(threads_list)):
            self.queue.put(None)
        
        for thread in threads_list:
            thread.join()
        
        progress_bar.close()
        
        self.end_time = datetime.now()
        
        # Trier les ports ouverts
        self.open_ports.sort(key=lambda x: x['port'])
        
        return self.get_results()
    
    def get_results(self):
        """
        Retourne les résultats du scan
        """
        duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            'target': self.target,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': duration,
            'total_ports': len(self.ports),
            'open_ports': self.open_ports,
            'closed_ports': len(self.closed_ports),
            'filtered_ports': len(self.filtered_ports),
            'scan_speed': len(self.ports) / duration if duration > 0 else 0
        }
    
    def quick_scan(self, common_ports_only=True):
        """
        Scan rapide des ports les plus communs
        """
        from port_db import get_common_ports_list
        
        if common_ports_only:
            self.ports = get_common_ports_list()
        
        return self.scan()