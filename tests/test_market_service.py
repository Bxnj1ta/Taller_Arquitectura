from django.test import TestCase
from unittest.mock import patch, MagicMock
from items.services.market_service import obtener_parametros_activos

class TestMarketService(TestCase):
    """Pruebas específicas para el servicio de mercado"""
    
    @patch('items.services.market_service.MarketDataService.obtener_datos_completos')
    def test_obtener_parametros_activos(self, mock_datos_mercado):
        """Prueba que el servicio de mercado procesa datos correctamente"""
        print("📊 Probando servicio de mercado con MOCK...")
        
        # Simular respuesta de APIs externas
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
        
        # Verificar estructura
        self.assertIn("CDT Bancario", parametros)
        self.assertIn("S&P 500", parametros)
        self.assertIn("Cripto (BTC)", parametros)
        self.assertIn("NFTs", parametros)
        
        # Verificar cálculos
        cdt_params = parametros["CDT Bancario"]
        self.assertIn("retorno", cdt_params)
        self.assertIn("volatilidad", cdt_params)
        self.assertIn("recomendacion", cdt_params)
        
        print(f"✅ CDT - Retorno: {cdt_params['retorno']*100:.2f}%")
        print(f"✅ S&P 500 - Retorno: {parametros['S&P 500']['retorno']*100:.2f}%")
        print("✓ Servicio de mercado con MOCK PASADO")