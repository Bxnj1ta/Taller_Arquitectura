from django.test import TestCase
from unittest.mock import patch, MagicMock
from items.views import _ejecutar_simulacion

class TestSimulacionConMock(TestCase):
    """Pruebas unitarias usando Mocks para APIs externas"""
    
    @patch('items.views.obtener_parametros_activos')
    def test_simulacion_con_mock_apis(self, mock_obtener_parametros):
        """Prueba que la simulación funciona con datos mock de APIs"""
        print("🧪 Probando simulación con MOCK de APIs...")
        
        # Configurar el mock para simular datos de APIs
        mock_obtener_parametros.return_value = {
            "CDT Bancario": {
                "retorno": 0.0077,
                "volatilidad": 0.001,
                "recomendacion": "Bajo riesgo",
                "info": {"fuente": "Mock", "tasa": 0.0925}
            },
            "S&P 500": {
                "retorno": 0.0246, 
                "volatilidad": 0.0297,
                "recomendacion": "Riesgo moderado",
                "info": {"fuente": "Mock Alpha Vantage"}
            },
            "Cripto (BTC)": {
                "retorno": 0.0252,
                "volatilidad": 0.0821, 
                "recomendacion": "Alto riesgo",
                "info": {"fuente": "Mock CoinGecko"}
            },
            "NFTs": {
                "retorno": 0.0200,
                "volatilidad": 0.0800,
                "recomendacion": "Alto riesgo",
                "info": {"fuente": "Mock Simulado"}
            }
        }
        
        # Datos de prueba
        monto = 1000000
        meses = 12
        
        # Ejecutar función REAL con datos MOCK
        resultados = _ejecutar_simulacion(monto, meses, mock_obtener_parametros.return_value)
        
        # Verificaciones
        self.assertIn("CDT Bancario", resultados)
        self.assertIn("S&P 500", resultados)
        
        cdt = resultados["CDT Bancario"]
        spy = resultados["S&P 500"]
        
        # Verificar lógica financiera
        self.assertGreater(cdt["esperado"], monto)
        self.assertGreater(spy["esperado"], cdt["esperado"])  # SP500 > CDT
        self.assertGreater(spy["mejor"], spy["esperado"])     # Mejor caso > Esperado
        self.assertLess(spy["peor"], spy["esperado"])         # Peor caso < Esperado
        
        print(f"✅ CDT Mock: ${cdt['esperado']:,.0f}")
        print(f"✅ S&P 500 Mock: ${spy['esperado']:,.0f}")
        print("✓ Prueba unitaria con MOCK PASADA")

    def test_limites_seguridad(self):
        """Prueba que la función maneja casos extremos correctamente"""
        print("🧪 Probando límites de seguridad...")
        
        activos_extremos = {
            "CDT Bancario": {
                "retorno": 0.50,  # ¡50% mensual! (irreal)
                "volatilidad": 0.001,
                "recomendacion": "Test"
            }
        }
        
        monto = 1000000
        meses = 120
        
        # Ejecutar con parámetros extremos
        resultados = _ejecutar_simulacion(monto, meses, activos_extremos)
        cdt = resultados["CDT Bancario"]
        
        # Verificar que aplica límites realistas (máximo 2.5x en 10 años)
        self.assertLess(cdt["esperado"], monto * 2.6)
        print(f"✅ Límite aplicado: ${cdt['esperado']:,.0f} (máximo realista)")
        print("✓ Límites de seguridad PASADOS")