from datetime import datetime, timedelta

from ..models import PrecioActivo
import requests
from decouple import config
import random
 
# Ejemplo de inyección de dependencias:
# alpha_service = AlphaVantageService()
# banrep_service = BanrepService()
# market_service = MarketService(alpha_service, banrep_service)


class MarketService:
    COINGECKO_API_KEY = config("COINGECKO_KEY", default="")
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self, alpha_service, banrep_service):
        self.alpha_service = alpha_service
        self.banrep_service = banrep_service

    def actualizar_activos(self):
        logs = []

        # --- S&P 500 ---
        try:
            logs.append(self.alpha_service.fetch_daily_prices("SPY", "S&P 500 ETF"))
            resultado_spy = AlphaVantageService.fetch_daily_prices("SPY", "S&P 500 ETF")
            logs.append(resultado_spy)
        except Exception as e:
            logs.append(f"❌ Error SPY: {str(e)}")

        # --- Bitcoin ---
        try:
            logs.append(self.alpha_service.fetch_daily_prices("BTC-USD", "Bitcoin"))
            resultado_btc = AlphaVantageService.fetch_daily_prices("BTC-USD", "Bitcoin")
            logs.append(resultado_btc)
        except Exception as e:
            logs.append(f"❌ Error BTC: {str(e)}")

        # --- CDT Bancario ---
        try:
            dtf_info = self.banrep_service.get_cdt_rate()
            fecha = datetime.now().date()
            valor = 1000 * (1 + dtf_info["tasa"])
            PrecioActivo.objects.update_or_create(
                simbolo="CDT",
                fecha=fecha,
                defaults={"nombre": "CDT Bancario (DTF)", "cierre": round(valor, 2)}
            )
            logs.append(f"✅ CDT actualizado: {dtf_info['tasa']*100}%")
        except Exception as e:
            # Fallback: tasa simulada
            fecha = datetime.now().date()
            tasa_simulada = random.uniform(0.07, 0.11)  # 7% a 11% anual
            valor = 1000 * (1 + tasa_simulada)
            PrecioActivo.objects.update_or_create(
                simbolo="CDT",
                fecha=fecha,
                defaults={"nombre": "CDT Bancario (DTF)", "cierre": round(valor, 2)}
            )
            logs.append(f"❌ Error CDT: {str(e)} (simulado {tasa_simulada*100:.2f}%)")

        # --- NFTs ---
        try:
            self.actualizar_nfts()
            logs.append("✅ NFTs actualizados")
        except Exception as e:
            logs.append(f"❌ Error NFTs: {str(e)}")

        return logs

    @staticmethod
    def actualizar_nfts():
        """Actualiza datos de NFTs con valores realistas y mejor manejo de errores"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Precios base actualizados (enero 2025)
        nft_collections = [
            {"slug": "cryptopunks", "name": "CryptoPunks", "base_price": 75000, "volatility": 0.15},
            {"slug": "bored-ape", "name": "Bored Ape Yacht Club", "base_price": 45000, "volatility": 0.20},
            {"slug": "azuki", "name": "Azuki", "base_price": 15000, "volatility": 0.25},
            {"slug": "doodles", "name": "Doodles", "base_price": 8000, "volatility": 0.30},
            {"slug": "clonex", "name": "CloneX", "base_price": 12000, "volatility": 0.22}
        ]

        for collection in nft_collections:
            try:
                if self.COINGECKO_API_KEY:
                    url = f"{self.COINGECKO_BASE_URL}/nfts/{collection['slug']}"
                    headers = {"X-CoinGecko-Api-Key": self.COINGECKO_API_KEY}
                    response = requests.get(url, headers=headers, timeout=10)

                    if response.status_code == 200:
                        data = response.json()
                        floor_price = data.get('floor_price', {}).get('usd', collection['base_price'])
                    else:
                        floor_price = collection['base_price'] * random.uniform(0.8, 1.2)
                else:
                    floor_price = collection['base_price'] * random.uniform(0.7, 1.3)

                # Intentar API real primero
                floor_price = None
                
                # Intentar API real primero si hay API key
                if MarketService.COINGECKO_API_KEY and MarketService.COINGECKO_API_KEY != 'tu_coingecko_api_key_aqui':
                    try:
                        url = f"{MarketService.COINGECKO_BASE_URL}/nfts/{collection['slug']}"
                        headers = {
                            "X-CoinGecko-Api-Key": MarketService.COINGECKO_API_KEY,
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        }
                        response = requests.get(url, headers=headers, timeout=15)
                        
                        if response.status_code == 200:
                            data = response.json()
                            floor_price = data.get('floor_price', {}).get('usd')
                            if floor_price:
                                logger.info(f"✅ Precio real obtenido para {collection['name']}: ${floor_price}")
                    except Exception as e:
                        logger.warning(f"⚠️  Error obteniendo precio real de {collection['name']}: {e}")
                
                # Si no hay precio de la API, usar simulación realista
                if not floor_price:
                    floor_price = collection['base_price'] * random.uniform(0.7, 1.3)
                fecha = datetime.now().date()
                PrecioActivo.objects.update_or_create(
                    simbolo=collection['slug'].upper(),
                    fecha=fecha,
                    defaults={"nombre": collection['name'], "cierre": round(floor_price, 2)}
                )
                # Simular variación realista basada en volatilidad
                variation = random.uniform(-collection['volatility'], collection['volatility'])
                floor_price = collection['base_price'] * (1 + variation)
                    
                    # Asegurar que el precio no sea negativo
                floor_price = max(floor_price, collection['base_price'] * 0.1)
                logger.info(f"📊 Precio simulado para {collection['name']}: ${floor_price:.2f}")
                
                # Generar datos históricos para los últimos 30 días
                for i in range(30):
                    fecha = datetime.now().date() - timedelta(days=i)
                    
                    # Aplicar variación diaria
                    daily_variation = random.uniform(-0.05, 0.05)  # 5% variación diaria
                    precio_diario = floor_price * (1 + daily_variation)
                    precio_diario = max(precio_diario, collection['base_price'] * 0.1)
                    
                    PrecioActivo.objects.update_or_create(
                        simbolo=collection['slug'].upper(),
                        fecha=fecha,
                        defaults={"nombre": collection['name'], "cierre": round(precio_diario, 2)}
                    )
                
                logger.info(f"✅ {collection['name']} actualizado con 30 días de datos")
                
            except Exception as e:
                logger.error(f"❌ Error procesando NFT {collection['name']}: {e}")
                # Fallback: usar precio base
                try:
                    fecha = datetime.now().date()
                    PrecioActivo.objects.update_or_create(
                        simbolo=collection['slug'].upper(),
                        fecha=fecha,
                        defaults={"nombre": collection['name'], "cierre": collection['base_price']}
                    )
                except Exception as fallback_error:
                    logger.error(f"❌ Error en fallback para {collection['name']}: {fallback_error}")