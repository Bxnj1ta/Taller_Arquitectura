from django.test import TestCase
from unittest.mock import patch
from items.services.market_service import obtener_parametros_activos

class TestMarketService(TestCase):
    
    @patch('items.services.market_service.MarketDataService.obtener_datos_completos')
    def test_obtener_parametros_activos(self, mock_datos_mercado):
        """Prueba que el servicio de mercado procesa datos correctamente"""
        print("📊 Probando servicio de mercado con MOCK...")
        
        # Mock de datos de API - SIMULAR LO QUE TU CÓDIGO REAL ESPERA
        mock_datos_mercado.return_value = {
            'cdt': {
                'tasa': 0.0925, 
                'fuente': 'Mock BanRep',
                'precios': [1.0, 1.01, 1.02]
            },
            'sp500': {
                'retorno': 0.0246,
                'volatilidad': 0.0297,
                'fuente': 'Mock Alpha Vantage',
                'precios': [4500, 4550, 4600]
            },
            'btc': {
                'retorno': 0.0252,
                'volatilidad': 0.0821, 
                'fuente': 'Mock CoinGecko',
                'precios': [50000, 51000, 49000]
            },
            'nfts': {
                'retorno': 0.0200,
                'volatilidad': 0.0800,
                'fuente': 'Mock Simulado',
                'precios': [1000, 1100, 900]
            }
        }
        
        # Ejecutar servicio REAL
        parametros = obtener_parametros_activos()
        
        # ✅ VERIFICAR ESTRUCTURA REAL (no la que imaginamos)
        self.assertIn("CDT Bancario", parametros)
        self.assertIn("S&P 500", parametros)
        self.assertIn("Cripto (BTC)", parametros)
        self.assertIn("NFTs", parametros)
        
        # Verificar campos que SÍ existen en tu código
        cdt_params = parametros["CDT Bancario"]
        self.assertIn("retorno", cdt_params)
        self.assertIn("volatilidad", cdt_params)
        self.assertIn("info", cdt_params)  # ✅ Este campo SÍ existe
        
        # Verificar tipos de datos
        self.assertIsInstance(cdt_params["retorno"], (int, float))
        self.assertIsInstance(cdt_params["volatilidad"], (int, float))
        
        print(f"✅ CDT - Retorno: {cdt_params['retorno']*100:.4f}%")
        print(f"✅ S&P 500 - Retorno: {parametros['S&P 500']['retorno']*100:.4f}%")
        print(f"✅ BTC - Volatilidad: {parametros['Cripto (BTC)']['volatilidad']*100:.4f}%")
        print("✓ Servicio de mercado con MOCK PASADO")
    
    def test_estructura_datos_activos(self):
        """Prueba adicional: verificar estructura completa de datos"""
        print("📋 Verificando estructura de datos...")
        
        # Usar mock mínimo para probar estructura
        with patch('items.services.market_service.MarketDataService.obtener_datos_completos') as mock:
            mock.return_value = {
                'cdt': {'tasa': 0.09, 'fuente': 'Test', 'precios': [1.0]},
                'sp500': {'retorno': 0.02, 'volatilidad': 0.03, 'fuente': 'Test', 'precios': [100]},
                'btc': {'retorno': 0.03, 'volatilidad': 0.08, 'fuente': 'Test', 'precios': [100]},
                'nfts': {'retorno': 0.02, 'volatilidad': 0.08, 'fuente': 'Test', 'precios': [100]}
            }
            
            parametros = obtener_parametros_activos()
            
            # Verificar que todos los activos tienen estructura consistente
            for activo, datos in parametros.items():
                self.assertIn("retorno", datos)
                self.assertIn("volatilidad", datos)
                self.assertIn("info", datos)
                self.assertIsInstance(datos["retorno"], (int, float))
                self.assertGreaterEqual(datos["retorno"], 0)  # Retorno no negativo
                
            print(f"✅ Estructura validada para {len(parametros)} activos")
            print("✓ Estructura de datos PASADA")