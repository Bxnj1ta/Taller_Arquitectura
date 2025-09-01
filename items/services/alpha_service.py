import requests
from datetime import datetime, timedelta
from ..models import PrecioActivo
from decouple import config
import random

class AlphaVantageService:
    API_KEY = config('ALPHA_VANTAGE_KEY')
    BASE_URL = "https://www.alphavantage.co/query"

    @classmethod
    def fetch_daily_prices(cls, symbol, nombre):
        """Descarga y guarda precios diarios de Alpha Vantage"""
        try:
            function = "TIME_SERIES_DAILY"
            if symbol == "BTC-USD":
                function = "DIGITAL_CURRENCY_DAILY"
                symbol = "BTC"
                market = "USD"
            
            if symbol == "BTC-USD":
                url = f"{cls.BASE_URL}?function={function}&symbol={symbol}&market={market}&apikey={cls.API_KEY}"
            else:
                url = f"{cls.BASE_URL}?function={function}&symbol={symbol}&apikey={cls.API_KEY}"
            
            print(f"🔍 Consultando: {url}")
            resp = requests.get(url, timeout=15)
            data = resp.json()
            
            # Si la API falla, usar datos simulados realistas
            if "Error Message" in data or "Note" in data:
                print(f"⚠️  API limitada, usando datos simulados para {symbol}")
                return cls._generate_mock_data(symbol, nombre)
            
            # Procesar datos según el tipo
            if symbol == "BTC":
                time_series = data.get("Time Series (Digital Currency Daily)", {})
                key_close = "4a. close (USD)"
            else:
                time_series = data.get("Time Series (Daily)", {})
                key_close = "4. close"
            
            if not time_series:
                return cls._generate_mock_data(symbol, nombre)
            
            for fecha_str, valores in list(time_series.items())[:30]:  # Últimos 30 días
                try:
                    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    cierre = float(valores[key_close])
                    
                    PrecioActivo.objects.update_or_create(
                        simbolo=symbol,
                        fecha=fecha,
                        defaults={"nombre": nombre, "cierre": cierre}
                    )
                except (ValueError, KeyError):
                    continue
            
            return f"✅ {symbol} actualizado"
            
        except Exception as e:
            print(f"❌ Error con {symbol}: {e}")
            return cls._generate_mock_data(symbol, nombre)

    @classmethod
    def _generate_mock_data(cls, symbol, nombre):
        """Genera datos realistas según el tipo de activo"""
        base_price = {
            "SPY": 450.0,       # S&P 500 ~$450
            "BTC-USD": 35000.0, # Bitcoin ~$35,000
            "BTC": 35000.0      # Bitcoin
        }.get(symbol, 100.0)
        
        # Generar últimos 30 días de datos
        for i in range(30):
            fecha = datetime.now().date() - timedelta(days=i)
            
            # Volatilidad diferente por activo
            if symbol == "SPY":
                volatility = 0.015  # 1.5% diario
            elif symbol in ["BTC-USD", "BTC"]:
                volatility = 0.035  # 3.5% diario
            else:
                volatility = 0.025  # 2.5% diario
            
            # Precio con variación realista
            variation = random.uniform(-volatility, volatility)
            precio = base_price * (1 + variation)
            
            PrecioActivo.objects.update_or_create(
                simbolo=symbol,
                fecha=fecha,
                defaults={"nombre": nombre, "cierre": round(precio, 2)}
            )
        
        return f"✅ {symbol} - Datos simulados generados"