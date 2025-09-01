import requests
from datetime import datetime
import random

class BanrepService:
    
    # Tasas DTF históricas reales (puedes actualizar manualmente)
    TASAS_HISTORICAS = {
        '2025-08': 8.80,  
        '2025-07': 8.93,  
        '2025-06': 8.96,  
        '2025-05': 8.86,  
    }

    @staticmethod
    def get_cdt_rate():
        """
        Obtiene la tasa DTF con múltiples fallbacks realistas
        """
        endpoints = [
            "https://www.banrep.gov.co/estadisticas/rest/secure/estseriesopen/data/220003/json",
            "https://www.banrep.gov.co/SeriesEstadisticas_Web/rest/secure/estseriesopen/data/220003/json",
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }

        for endpoint in endpoints:
            try:
                print(f"🔍 Intentando BanRep: {endpoint}")
                response = requests.get(endpoint, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if "Data" in data and data["Data"]:
                        ultimo = data["Data"][-1]
                        tasa_anual = float(ultimo["Valor"]) / 100.0
                        periodo = ultimo["Periodo"]
                        print(f"✅ Tasa DTF real: {tasa_anual*100}%")
                        return {"tasa": tasa_anual, "periodo": periodo}
                
            except Exception:
                continue
        
        # Fallback a datos históricos reales
        ultimo_mes = list(BanrepService.TASAS_HISTORICAS.keys())[0]
        tasa_anual = BanrepService.TASAS_HISTORICAS[ultimo_mes] / 100.0
        print(f"⚠️  Usando tasa histórica DTF: {tasa_anual*100}%")
        return {"tasa": tasa_anual, "periodo": ultimo_mes + "-01"}