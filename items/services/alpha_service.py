import requests
from datetime import datetime, timedelta
from ..models import PrecioActivo
from decouple import config
import random
import logging

logger = logging.getLogger(__name__)

class AlphaVantageService:
    API_KEY = config('ALPHA_VANTAGE_KEY', default='')
    BASE_URL = "https://www.alphavantage.co/query"

    @classmethod
    def fetch_daily_prices(cls, symbol, nombre):
        """Descarga y guarda precios diarios de Alpha Vantage con mejor manejo de errores"""
        
        # Si no hay API key, usar datos simulados directamente
        if not cls.API_KEY or cls.API_KEY == 'tu_alpha_vantage_api_key_aqui':
            logger.warning(f"⚠️  Sin API key de Alpha Vantage, usando datos simulados para {symbol}")
            return cls._generate_mock_data(symbol, nombre)
        
        try:
            # Configurar parámetros según el tipo de activo
            if symbol == "BTC-USD":
                function = "DIGITAL_CURRENCY_DAILY"
                symbol_param = "BTC"
                market = "USD"
                url = f"{cls.BASE_URL}?function={function}&symbol={symbol_param}&market={market}&apikey={cls.API_KEY}"
            else:
                function = "TIME_SERIES_DAILY"
                symbol_param = symbol
                url = f"{cls.BASE_URL}?function={function}&symbol={symbol_param}&apikey={cls.API_KEY}"
            
            logger.info(f"🔍 Consultando Alpha Vantage: {symbol}")
            
            # Headers para evitar bloqueos
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            resp = requests.get(url, headers=headers, timeout=20)
            
            # Verificar status code
            if resp.status_code != 200:
                logger.warning(f"⚠️  Status {resp.status_code} para {symbol}, usando datos simulados")
                return cls._generate_mock_data(symbol, nombre)
            
            data = resp.json()
            
            # Verificar errores de la API
            if "Error Message" in data:
                logger.error(f"❌ Error de Alpha Vantage para {symbol}: {data['Error Message']}")
                return cls._generate_mock_data(symbol, nombre)
            
            if "Note" in data:
                logger.warning(f"⚠️  Límite de API alcanzado para {symbol}: {data['Note']}")
                return cls._generate_mock_data(symbol, nombre)
            
            if "Information" in data:
                logger.warning(f"⚠️  Información de API para {symbol}: {data['Information']}")
                return cls._generate_mock_data(symbol, nombre)
            
            # Procesar datos según el tipo
            if symbol == "BTC-USD":
                time_series = data.get("Time Series (Digital Currency Daily)", {})
                # Intentar diferentes claves para el precio de cierre
                key_close = None
                for key in ["4a. close (USD)", "4b. close (USD)", "4. close (USD)", "close"]:
                    if key in list(time_series.values())[0] if time_series else False:
                        key_close = key
                        break
                if not key_close:
                    logger.warning(f"⚠️  No se encontró clave de precio para {symbol}")
                    return cls._generate_mock_data(symbol, nombre)
            else:
                time_series = data.get("Time Series (Daily)", {})
                key_close = "4. close"
            
            if not time_series:
                logger.warning(f"⚠️  Sin datos de series temporales para {symbol}")
                return cls._generate_mock_data(symbol, nombre)
            
            # Procesar y guardar datos
            registros_guardados = 0
            for fecha_str, valores in list(time_series.items())[:30]:  # Últimos 30 días
                try:
                    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    cierre = float(valores[key_close])
                    
                    PrecioActivo.objects.update_or_create(
                        simbolo=symbol,
                        fecha=fecha,
                        defaults={"nombre": nombre, "cierre": cierre}
                    )
                    registros_guardados += 1
                except (ValueError, KeyError) as e:
                    logger.warning(f"⚠️  Error procesando fecha {fecha_str} para {symbol}: {e}")
                    continue
            
            if registros_guardados > 0:
                logger.info(f"✅ {symbol} actualizado: {registros_guardados} registros")
                return f"✅ {symbol} actualizado ({registros_guardados} registros)"
            else:
                logger.warning(f"⚠️  No se guardaron registros para {symbol}")
                return cls._generate_mock_data(symbol, nombre)
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout consultando Alpha Vantage para {symbol}")
            return cls._generate_mock_data(symbol, nombre)
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión con Alpha Vantage para {symbol}: {e}")
            return cls._generate_mock_data(symbol, nombre)
        except Exception as e:
            logger.error(f"❌ Error inesperado con {symbol}: {e}")
            return cls._generate_mock_data(symbol, nombre)

    @classmethod
    def _generate_mock_data(cls, symbol, nombre):
        """Genera datos realistas según el tipo de activo con precios actualizados"""
        
        # Precios base más actualizados (enero 2025)
        base_prices = {
            "SPY": 580.0,       # S&P 500 ETF ~$580
            "BTC-USD": 95000.0, # Bitcoin ~$95,000
            "BTC": 95000.0,     # Bitcoin
            "CRYPTOPUNKS": 75000.0,  # CryptoPunks NFT
            "BORED-APE": 45000.0,    # Bored Ape Yacht Club
            "AZUKI": 15000.0         # Azuki NFT
        }
        
        base_price = base_prices.get(symbol, 100.0)
        
        # Generar últimos 30 días de datos con tendencia realista
        registros_guardados = 0
        for i in range(30):
            fecha = datetime.now().date() - timedelta(days=i)
            
            # Volatilidad diferente por activo
            if symbol == "SPY":
                volatility = 0.012  # 1.2% diario (menos volátil)
                trend = 0.0002      # Tendencia ligeramente alcista
            elif symbol in ["BTC-USD", "BTC"]:
                volatility = 0.045  # 4.5% diario (muy volátil)
                trend = 0.0005      # Tendencia alcista
            elif symbol in ["CRYPTOPUNKS", "BORED-APE", "AZUKI"]:
                volatility = 0.08   # 8% diario (extremadamente volátil)
                trend = 0.001       # Tendencia alcista fuerte
            else:
                volatility = 0.025  # 2.5% diario
                trend = 0.0001      # Tendencia neutra
            
            # Aplicar tendencia temporal (más reciente = más alto)
            time_factor = 1 + (trend * (30 - i))
            
            # Precio con variación realista y tendencia
            variation = random.uniform(-volatility, volatility)
            precio = base_price * time_factor * (1 + variation)
            
            # Asegurar que el precio no sea negativo
            precio = max(precio, base_price * 0.1)
            
            try:
                PrecioActivo.objects.update_or_create(
                    simbolo=symbol,
                    fecha=fecha,
                    defaults={"nombre": nombre, "cierre": round(precio, 2)}
                )
                registros_guardados += 1
            except Exception as e:
                logger.warning(f"⚠️  Error guardando datos simulados para {symbol} en {fecha}: {e}")
                continue
        
        logger.info(f"✅ {symbol} - {registros_guardados} registros simulados generados")
        return f"✅ {symbol} - Datos simulados generados ({registros_guardados} registros)"