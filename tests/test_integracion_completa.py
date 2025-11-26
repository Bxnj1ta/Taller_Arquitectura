from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from unittest.mock import patch
import json

User = get_user_model()

class TestIntegracionCompleta(TestCase):
    """Pruebas de integración completa con mocks"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@integracion.com',
            password='testpass123'
        )
    
    @patch('items.services.market_service.MarketDataService.obtener_datos_completos')
    def test_flujo_completo_con_mock(self, mock_datos_mercado):
        """Prueba completa: login → simulación → BD con APIs mock"""
        print("🔗 Probando flujo COMPLETO con APIs mock...")
        
        # Configurar mock de APIs - ESTRUCTURA CORREGIDA
        mock_datos_mercado.return_value = {
            'cdt': {
                'tasa': 0.0925, 
                'fuente': 'Mock BanRep',
                'precios': [1.0, 1.01, 1.02],
                'info': {  # ✅ AGREGAR ESTO
                    'fuente': 'Mock BanRep',
                    'tasa': 0.0925,
                    'periodo': 'Mock'
                }
            },
            'sp500': {
                'retorno': 0.0246,
                'volatilidad': 0.0297,
                'fuente': 'Mock Alpha Vantage', 
                'precios': [4500, 4550, 4600],
                'info': {  # ✅ AGREGAR ESTO
                    'fuente': 'Mock Alpha Vantage'
                }
            },
            'btc': {
                'retorno': 0.0252,
                'volatilidad': 0.0821,
                'fuente': 'Mock CoinGecko',
                'precios': [50000, 51000, 49000],
                'info': {  # ✅ AGREGAR ESTO
                    'fuente': 'Mock CoinGecko'
                }
            },
            'nfts': {
                'retorno': 0.0200,
                'volatilidad': 0.0800,
                'fuente': 'Mock Simulado',
                'precios': [1000, 1100, 900],
                'info': {  # ✅ AGREGAR ESTO
                    'fuente': 'Mock Simulado'
                }
            }
        }
        
        # 1. Login
        login_exitoso = self.client.login(email='test@integracion.com', password='testpass123')
        self.assertTrue(login_exitoso)
        print("✅ Login exitoso")
        
        # 2. Simulación con datos mock
        datos = {"monto": 2000000, "meses": 12}
        
        respuesta = self.client.post(
            '/api/simular/',
            data=json.dumps(datos),
            content_type='application/json'
        )
        
        # 3. Verificar respuesta
        self.assertEqual(respuesta.status_code, 200, "La API debería responder 200")
        datos_respuesta = respuesta.json()
        
        self.assertIn("resultados", datos_respuesta)
        self.assertIn("CDT Bancario", datos_respuesta["resultados"])
        self.assertIn("metadata", datos_respuesta)
        
        resultados = datos_respuesta["resultados"]
        metadata = datos_respuesta["metadata"]
        
        # Verificar lógica financiera
        self.assertGreater(resultados["S&P 500"]["esperado"], resultados["CDT Bancario"]["esperado"])
        
        # Verificar metadata
        self.assertIn("fuentes", metadata)
        self.assertEqual(metadata["fuentes"]["cdt"], "Mock BanRep")
        
        print(f"✅ CDT: ${float(resultados['CDT Bancario']['esperado']):,.0f}")
        print(f"✅ S&P 500: ${float(resultados['S&P 500']['esperado']):,.0f}")
        print(f"✅ Metadata: {metadata['fuentes']['cdt']}")
        print("✓ Flujo completo con MOCK PASADO")