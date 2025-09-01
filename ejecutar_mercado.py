# ejecutar_mercado.py
import os
import django
import sys

# Configurar Django
sys.path.append(r'C:\Users\benja\OneDrive\Escritorio\ArquitecturaSoftware\soa_crud')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soa_crud.settings')
django.setup()

from items.models import PrecioActivo
from datetime import datetime

print("🔄 Iniciando actualización...")
logs = []

# --- S&P 500 ---
try:
    spy_price = 450.0 + (datetime.now().day % 10)
    PrecioActivo.objects.update_or_create(
        simbolo="SPY",
        fecha=datetime.now().date(),
        defaults={"nombre": "S&P 500 ETF", "cierre": spy_price}
    )
    logs.append(f"✅ SPY: ${spy_price:.2f}")
except Exception as e:
    logs.append(f"❌ Error SPY: {str(e)}")

# --- Bitcoin ---
try:
    btc_price = 35000.0 + (datetime.now().day % 20) * 100
    PrecioActivo.objects.update_or_create(
        simbolo="BTC",
        fecha=datetime.now().date(),
        defaults={"nombre": "Bitcoin", "cierre": btc_price}
    )
    logs.append(f"✅ BTC: ${btc_price:.2f}")
except Exception as e:
    logs.append(f"❌ Error BTC: {str(e)}")

# --- CDT ---
try:
    cdt_rate = 0.0825
    cdt_value = 1000 * (1 + cdt_rate)
    PrecioActivo.objects.update_or_create(
        simbolo="CDT",
        fecha=datetime.now().date(),
        defaults={"nombre": "CDT Bancario", "cierre": cdt_value}
    )
    logs.append(f"✅ CDT: {cdt_rate*100:.2f}%")
except Exception as e:
    logs.append(f"❌ Error CDT: {str(e)}")

# --- NFTs ---
try:
    nft_price = 50000.0 + (datetime.now().day % 15) * 2000
    PrecioActivo.objects.update_or_create(
        simbolo="NFT",
        fecha=datetime.now().date(),
        defaults={"nombre": "CryptoPunks NFT", "cierre": nft_price}
    )
    logs.append(f"✅ NFT: ${nft_price:.2f}")
except Exception as e:
    logs.append(f"❌ Error NFT: {str(e)}")

print("📊 RESULTADOS:")
for r in logs:
    print(r)

print("\n🔍 DATOS GUARDADOS:")
hoy = datetime.now().date()
for item in PrecioActivo.objects.filter(fecha=hoy):
    print(f"{item.nombre}: ${item.cierre:.2f}")