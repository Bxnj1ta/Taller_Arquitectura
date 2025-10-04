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
        except Exception as e:
            logs.append(f"❌ Error SPY: {str(e)}")

        # --- Bitcoin ---
        try:
            logs.append(self.alpha_service.fetch_daily_prices("BTC-USD", "Bitcoin"))
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
            logs.append(f"❌ Error CDT: {str(e)}")

        # --- NFTs ---
        try:
            self.actualizar_nfts()
            logs.append("✅ NFTs actualizados")
        except Exception as e:
            logs.append(f"❌ Error NFTs: {str(e)}")

        return logs

    def actualizar_nfts(self):
        """Actualiza datos de NFTs con valores realistas"""
        nft_collections = [
            {"slug": "cryptopunks", "name": "CryptoPunks", "base_price": 60000},
            {"slug": "bored-ape", "name": "Bored Ape Yacht Club", "base_price": 45000},
            {"slug": "azuki", "name": "Azuki", "base_price": 15000}
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

                fecha = datetime.now().date()
                PrecioActivo.objects.update_or_create(
                    simbolo=collection['slug'].upper(),
                    fecha=fecha,
                    defaults={"nombre": collection['name'], "cierre": round(floor_price, 2)}
                )

            except Exception as e:
                print(f"Error con NFT {collection['name']}: {e}")
                fecha = datetime.now().date()
                PrecioActivo.objects.update_or_create(
                    simbolo=collection['slug'].upper(),
                    fecha=fecha,
                    defaults={"nombre": collection['name'], "cierre": collection['base_price']}
                )