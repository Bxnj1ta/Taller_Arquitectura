from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch
from items.models import Wallet

User = get_user_model()

class WalletTopUpTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='tester@example.com', password='pw')
        self.client.login(username='tester@example.com', password='pw')

    def test_top_up_increases_balance(self):
        wallet = Wallet.objects.get(user=self.user)
        payload = {
            'full_name': 'Tester Ejemplo',
            'card_number': '4242424242424242',
            'expiry_month': '12',
            'expiry_year': '2030',
            'cvv': '123',
            'amount': '150.00'
        }
        response = self.client.post(reverse('top_up'), payload, follow=True)
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal('150.00'))
        self.assertContains(response, "Se han agregado")

    @patch('items.views._ejecutar_simulacion')
    @patch('items.views.obtener_parametros_activos')
    def test_wallet_invest_uses_balance(self, mock_activos, mock_simulacion):
        wallet = Wallet.objects.get(user=self.user)
        wallet.balance = Decimal('500.00')
        wallet.save()

        mock_activos.return_value = {
            "CDT Bancario": {"retorno": 0.01, "volatilidad": 0.001, "info": {}},
            "S&P 500": {"retorno": 0.01, "volatilidad": 0.02, "info": {}},
            "Cripto (BTC)": {"retorno": 0.02, "volatilidad": 0.05, "info": {}},
            "NFTs": {"retorno": 0.03, "volatilidad": 0.08, "info": {}},
        }
        mock_simulacion.return_value = {
            "CDT Bancario": {"esperado": 110.0, "ganancia": 10.0, "ganancia_porcentaje": 10, "recomendacion": ""},
            "S&P 500": {"esperado": 0, "ganancia": 0, "ganancia_porcentaje": 0, "recomendacion": ""},
            "Cripto (BTC)": {"esperado": 0, "ganancia": 0, "ganancia_porcentaje": 0, "recomendacion": ""},
            "NFTs": {"esperado": 0, "ganancia": 0, "ganancia_porcentaje": 0, "recomendacion": ""},
        }

        response = self.client.post(
            reverse('wallet_invest'),
            {'asset': 'cdt', 'amount': '100', 'months': '12'},
            follow=True
        )

        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal('510.00'))
        self.assertContains(response, "Inversión en CDT Bancario ejecutada")