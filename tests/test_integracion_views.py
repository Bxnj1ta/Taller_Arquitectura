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
    
    @patch('items.views.obtener_parametros_activos')
    def test_flujo_completo_con_apis_mock(self, mock_obtener_parametros):
        """Prueba completa: login → simulación → BD con APIs mock"""
        print("🔗 Probando flujo COMPLETO con APIs mock...")
        
        # Configurar mock de APIs
        mock_obtener_parametros.return_value = {
            "CDT Bancario": {
                "retorno": 0.0077, "volatilidad": 0.001, "recomendacion": "Bajo riesgo"
            },
            "S&P 500": {
                "retorno": 0.0246, "volatilidad": 0.0297, "recomendacion": "Riesgo moderado"
            },
            "Cripto (BTC)": {
                "retorno": 0.0252, "volatilidad": 0.0821, "recomendacion": "Alto riesgo" 
            },
            "NFTs": {
                "retorno": 0.0200, "volatilidad": 0.0800, "recomendacion": "Alto riesgo"
            }
        }
        
        # 1. Login
        self.client.login(email='test@integracion.com', password='testpass123')
        print("✅ Login exitoso")
        
        # 2. Simulación con datos mock
        datos = {"monto": 2000000, "meses": 24}
        respuesta = self.client.post(
            '/api/simular/',
            data=json.dumps(datos),
            content_type='application/json'
        )
        
        self.assertEqual(respuesta.status_code, 200)
        datos_respuesta = respuesta.json()
        
        # 3. Verificar respuesta
        self.assertIn("resultados", datos_respuesta)
        self.assertIn("CDT Bancario", datos_respuesta["resultados"])
        self.assertIn("simulacion", datos_respuesta)
        
        resultados = datos_respuesta["resultados"]
        self.assertGreater(resultados["S&P 500"]["esperado"], resultados["CDT Bancario"]["esperado"])
        
        print(f"✅ CDT: ${resultados['CDT Bancario']['esperado']:,.0f}")
        print(f"✅ S&P 500: ${resultados['S&P 500']['esperado']:,.0f}")
        print("✓ Flujo completo con MOCK PASADO")