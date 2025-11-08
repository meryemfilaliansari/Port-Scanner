#!/usr/bin/env python3
"""
Tests unitaires pour le scanner de ports
"""
import unittest
import sys
from pathlib import Path

# Ajouter le dossier src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from scanner import PortScanner
from port_db import get_port_info, get_common_ports_list
from utils import validate_ip, validate_port_range, resolve_hostname

class TestPortDatabase(unittest.TestCase):
    """Tests pour la base de données des ports"""
    
    def test_get_port_info_known_port(self):
        """Test avec un port connu"""
        info = get_port_info(80)
        self.assertEqual(info['port'], 80)
        self.assertEqual(info['service'], 'HTTP')
        self.assertFalse(info['is_dangerous'])
    
    def test_get_port_info_dangerous_port(self):
        """Test avec un port dangereux"""
        info = get_port_info(23)
        self.assertEqual(info['port'], 23)
        self.assertTrue(info['is_dangerous'])
        self.assertIn('Telnet', info['danger_info'])
    
    def test_get_port_info_unknown_port(self):
        """Test avec un port inconnu"""
        info = get_port_info(12345)
        self.assertEqual(info['port'], 12345)
        self.assertEqual(info['service'], 'Unknown')
        self.assertFalse(info['is_dangerous'])
    
    def test_get_common_ports_list(self):
        """Test de la liste des ports communs"""
        ports = get_common_ports_list()
        self.assertIsInstance(ports, list)
        self.assertGreater(len(ports), 0)
        self.assertIn(80, ports)
        self.assertIn(443, ports)

class TestUtils(unittest.TestCase):
    """Tests pour les utilitaires"""
    
    def test_validate_ip_valid(self):
        """Test de validation d'IP valide"""
        self.assertTrue(validate_ip('127.0.0.1'))
        self.assertTrue(validate_ip('192.168.1.1'))
    
    def test_validate_ip_hostname(self):
        """Test de validation d'hostname"""
        self.assertTrue(validate_ip('localhost'))
        self.assertTrue(validate_ip('google.com'))
    
    def test_validate_ip_invalid(self):
        """Test de validation d'IP invalide"""
        self.assertFalse(validate_ip('999.999.999.999'))
        self.assertFalse(validate_ip('not-a-valid-hostname-12345.xyz'))
    
    def test_validate_port_range_single(self):
        """Test de validation d'un port unique"""
        ports = validate_port_range('80')
        self.assertEqual(ports, [80])
    
    def test_validate_port_range_multiple(self):
        """Test de validation de plusieurs ports"""
        ports = validate_port_range('80,443,8080')
        self.assertEqual(sorted(ports), [80, 443, 8080])
    
    def test_validate_port_range_range(self):
        """Test de validation d'une plage de ports"""
        ports = validate_port_range('80-85')
        self.assertEqual(ports, [80, 81, 82, 83, 84, 85])
    
    def test_validate_port_range_mixed(self):
        """Test de validation mixte"""
        ports = validate_port_range('80,443,8000-8002')
        self.assertEqual(sorted(ports), [80, 443, 8000, 8001, 8002])
    
    def test_validate_port_range_invalid(self):
        """Test de validation invalide"""
        self.assertIsNone(validate_port_range('invalid'))
        self.assertIsNone(validate_port_range('70000'))
    
    def test_resolve_hostname(self):
        """Test de résolution de hostname"""
        ip = resolve_hostname('localhost')
        self.assertIsNotNone(ip)
        self.assertIn(ip, ['127.0.0.1', '::1'])

class TestPortScanner(unittest.TestCase):
    """Tests pour le scanner de ports"""
    
    def test_scanner_initialization(self):
        """Test d'initialisation du scanner"""
        scanner = PortScanner('127.0.0.1', [80, 443], timeout=1, threads=10)
        self.assertEqual(scanner.target, '127.0.0.1')
        self.assertEqual(scanner.ports, [80, 443])
        self.assertEqual(scanner.timeout, 1)
        self.assertEqual(scanner.threads, 10)
    
    def test_scan_localhost(self):
        """Test de scan sur localhost (ports fermés normalement)"""
        scanner = PortScanner('127.0.0.1', [12345, 12346], timeout=0.5, threads=2)
        results = scanner.scan(verbose=False)
        
        self.assertIsNotNone(results)
        self.assertEqual(results['target'], '127.0.0.1')
        self.assertEqual(results['total_ports'], 2)
        self.assertGreaterEqual(results['duration'], 0)
    
    def test_get_results_structure(self):
        """Test de la structure des résultats"""
        scanner = PortScanner('127.0.0.1', [80], timeout=0.5, threads=1)
        results = scanner.scan(verbose=False)
        
        # Vérifier que toutes les clés nécessaires sont présentes
        required_keys = ['target', 'start_time', 'end_time', 'duration', 
                        'total_ports', 'open_ports', 'closed_ports', 
                        'filtered_ports', 'scan_speed']
        
        for key in required_keys:
            self.assertIn(key, results)

class TestReporter(unittest.TestCase):
    """Tests pour le générateur de rapports"""
    
    def setUp(self):
        """Préparer des résultats de test"""
        from datetime import datetime
        self.mock_results = {
            'target': '127.0.0.1',
            'start_time': datetime.now(),
            'end_time': datetime.now(),
            'duration': 1.5,
            'total_ports': 10,
            'open_ports': [
                {'port': 80, 'banner': 'Test'},
                {'port': 443, 'banner': ''}
            ],
            'closed_ports': 7,
            'filtered_ports': 1,
            'scan_speed': 6.67
        }
    
    def test_reporter_initialization(self):
        """Test d'initialisation du reporter"""
        from reporter import Reporter
        reporter = Reporter(self.mock_results)
        self.assertEqual(reporter.results['target'], '127.0.0.1')
    
    def test_console_report(self):
        """Test du rapport console (ne doit pas crasher)"""
        from reporter import Reporter
        reporter = Reporter(self.mock_results)
        try:
            reporter.print_console_report()
            success = True
        except:
            success = False
        self.assertTrue(success)

def run_tests():
    """Lance tous les tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter tous les tests
    suite.addTests(loader.loadTestsFromTestCase(TestPortDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestPortScanner))
    suite.addTests(loader.loadTestsFromTestCase(TestReporter))
    
    # Lancer les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)