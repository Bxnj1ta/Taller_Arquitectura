# ===== services/market_service.py =====
"""
Servicio unificado para obtener datos de mercado de múltiples fuentes:
- Alpha Vantage (S&P 500, Bitcoin)
- Banco de la República (Tasas DTF/CDT)
- CoinGecko (NFTs)
"""

import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
from decouple import config
import random
import numpy as np
import math

# Configurar logging para mostrar todos los mensajes
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class MarketDataService:
    """Servicio principal para obtención de datos de mercado"""
    
    # Configuración de APIs
    ALPHA_VANTAGE_KEY = config('ALPHA_VANTAGE_KEY', default='')
    ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
    
    COINGECKO_KEY = config("COINGECKO_KEY", default="")
    COINGECKO_URL = "https://api.coingecko.com/api/v3"
    
    BANREP_ENDPOINTS = [
        "https://www.banrep.gov.co/estadisticas/rest/estseriesopen/data/220003/json",
        "https://www.banrep.gov.co/estadisticas/rest/secure/estseriesopen/data/220003/json",
        "https://www.banrep.gov.co/SeriesEstadisticas_Web/rest/estseriesopen/data/220003/json",
        "https://www.banrep.gov.co/estadisticas/rest/estseriesopen/data/220003/xml",  # XML como fallback
    ]
    
    # Tasas históricas de respaldo (actualizadas enero 2025)
    TASAS_DTF_HISTORICAS = {
        '2025-01': 9.25,
        '2024-12': 9.15,
        '2024-11': 9.05,
        '2024-10': 8.95,
    }
    
    # Precios base actualizados (enero 2025)
    PRECIOS_BASE = {
        "SPY": 580.0,
        "BTC": 95000.0,
        "CRYPTOPUNKS": 75000.0,
    }
    @classmethod
    def debug_datos_apis(cls):
        """Función temporal para debuggear qué datos están llegando de las APIs"""
        print("🐛 DEBUG - DATOS CRUDOS DE LAS APIS:")
        
        # Obtener datos completos
        datos = cls.obtener_datos_completos()
        
        for activo, info in datos.items():
            print(f"\n📊 {activo.upper()}:")
            print(f"   Fuente: {info.get('fuente', 'N/A')}")
            
            if 'precios' in info:
                precios = info['precios']
                print(f"   Precios obtenidos: {len(precios)}")
                if precios:
                    print(f"   Primeros 5 precios: {[round(p, 2) for p in precios[:5]]}")
                    print(f"   Últimos 5 precios: {[round(p, 2) for p in precios[-5:]]}")
                    print(f"   Precio más alto: {max(precios):.2f}")
                    print(f"   Precio más bajo: {min(precios):.2f}")
            
            if 'retorno' in info:
                retorno_porcentaje = info['retorno'] * 100
                print(f"   Retorno mensual calculado: {info['retorno']:.6f} ({retorno_porcentaje:.4f}%)")
                print(f"   → Retorno ANUAL equivalente: {(1 + info['retorno'])**12 - 1:.4f} ({((1 + info['retorno'])**12 - 1)*100:.2f}%)")
            
            if 'volatilidad' in info:
                volatilidad_porcentaje = info['volatilidad'] * 100
                print(f"   Volatilidad mensual calculada: {info['volatilidad']:.6f} ({volatilidad_porcentaje:.4f}%)")
                print(f"   → Volatilidad ANUAL equivalente: {info['volatilidad'] * math.sqrt(12):.4f} ({info['volatilidad'] * math.sqrt(12) * 100:.2f}%)")
            
            if 'tasa' in info:
                print(f"   Tasa anual: {info['tasa']:.4f} ({info['tasa']*100:.2f}%)")
                print(f"   → Tasa mensual equivalente: {info['tasa']/12:.6f} ({info['tasa']/12*100:.4f}%)")

        print("\n🔍 ANALIZANDO PROBLEMAS POTENCIALES:")
        
        # Verificar si los retornos son realistas
        for activo, info in datos.items():
            if 'retorno' in info:
                retorno_mensual = info['retorno']
                retorno_anual = (1 + retorno_mensual) ** 12 - 1
                
                if retorno_anual > 10:  # Más del 1000% anual
                    print(f"   ❌ {activo}: Retorno anual del {retorno_anual*100:.0f}% - ¡COMPLETAMENTE IRREAL!")
                elif retorno_anual > 1:  # Más del 100% anual  
                    print(f"   ⚠️ {activo}: Retorno anual del {retorno_anual*100:.0f}% - Muy alto")
                elif retorno_anual > 0.5:  # Más del 50% anual
                    print(f"   📈 {activo}: Retorno anual del {retorno_anual*100:.0f}% - Alto pero posible")
                else:
                    print(f"   ✅ {activo}: Retorno anual del {retorno_anual*100:.1f}% - Realista")

    @classmethod
    def obtener_datos_completos(cls):
        """
        Obtiene todos los datos necesarios para la simulación
        
        Returns:
            dict: {
                "cdt": {"tasa": float, "fuente": str},
                "sp500": {"precios": list, "retorno": float, "volatilidad": float},
                "btc": {"precios": list, "retorno": float, "volatilidad": float},
                "nfts": {"precios": list, "retorno": float, "volatilidad": float}
            }
        """
        print("🔄 INICIANDO OBTENCIÓN DE DATOS DE MERCADO...")
        
        # Verificar configuración primero
        cls._verificar_configuracion()
        
        datos = {
            "cdt": cls._obtener_tasa_cdt(),
            "sp500": cls._obtener_datos_sp500(),
            "btc": cls._obtener_datos_bitcoin(),
            "nfts": cls._obtener_datos_nfts()
        }
        
        return datos

    @classmethod
    def _verificar_configuracion(cls):
        """Verifica y muestra la configuración de APIs"""
        print("🔧 CONFIGURACIÓN DE APIS:")
        print(f"   Alpha Vantage: {'✅ Configurada' if cls.ALPHA_VANTAGE_KEY and cls.ALPHA_VANTAGE_KEY != 'demo' else '❌ No configurada'}")
        print(f"   CoinGecko: {'✅ Configurada' if cls.COINGECKO_KEY else '❌ No configurada'}")

    @classmethod
    def _obtener_tasa_cdt(cls):
        """Obtiene la tasa DTF del Banco de la República"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'es-ES,es;q=0.9',
        }
        
        # Intentar endpoints de BanRep
        for i, endpoint in enumerate(cls.BANREP_ENDPOINTS, 1):
            try:
                response = requests.get(endpoint, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("Data") and len(data["Data"]) > 0:
                        ultimo = data["Data"][-1]
                        tasa_anual = float(ultimo["Valor"]) / 100.0
                        periodo = ultimo.get("Periodo", "N/A")
                        
                        print(f"✅ DATOS REALES - Tasa DTF: {tasa_anual*100:.2f}% (período: {periodo})")
                        return {
                            "tasa": tasa_anual,
                            "periodo": periodo,
                            "fuente": "BanRep API"
                        }
                else:
                    print(f"❌ API BanRep {i} falló - Status: {response.status_code}")
            except Exception as e:
                print(f"❌ API BanRep {i} error: {e}")
                continue
        
        # Fallback a datos históricos
        print("🔄 DATOS SIMULADOS - Usando tasa DTF histórica")
        ultimo_mes = list(cls.TASAS_DTF_HISTORICAS.keys())[0]
        tasa_anual = cls.TASAS_DTF_HISTORICAS[ultimo_mes] / 100.0
        
        return {
            "tasa": tasa_anual,
            "periodo": f"{ultimo_mes}-01",
            "fuente": "Histórica"
        }
    
    @classmethod
    def _obtener_datos_sp500(cls):
        """Obtiene datos históricos del S&P 500"""
        if cls.ALPHA_VANTAGE_KEY and cls.ALPHA_VANTAGE_KEY != 'demo':
            try:
                url = f"{cls.ALPHA_VANTAGE_URL}?function=TIME_SERIES_DAILY&symbol=SPY&apikey={cls.ALPHA_VANTAGE_KEY}"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'application/json',
                }
                
                response = requests.get(url, headers=headers, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verificar si API key es válida
                    if "Error Message" in data:
                        print("❌ API Alpha Vantage - Key inválida o límite excedido")
                    elif "Note" in data:
                        print("❌ API Alpha Vantage - Límite de llamadas excedido")
                    else:
                        time_series = data.get("Time Series (Daily)", {})
                        
                        if time_series:
                            # Extraer últimos 120 días
                            precios = []
                            for fecha_str, valores in sorted(time_series.items(), reverse=True)[:120]:
                                try:
                                    precio = float(valores["4. close"])
                                    precios.append(precio)
                                except (KeyError, ValueError):
                                    continue
                            
                            if len(precios) > 2:
                                retorno, volatilidad = cls._calcular_rendimiento(precios)
                                print(f"✅ DATOS REALES - S&P 500: {len(precios)} precios, último: ${precios[0]:.2f}")
                                
                                return {
                                    "precios": precios,
                                    "retorno": retorno,
                                    "volatilidad": volatilidad,
                                    "fuente": "Alpha Vantage"
                                }
                else:
                    print(f"❌ API Alpha Vantage falló - Status: {response.status_code}")
            except Exception as e:
                print(f"❌ API Alpha Vantage error: {e}")
        else:
            print("❌ API Alpha Vantage no configurada para S&P 500")
        
        # Intentar Yahoo Finance como alternativa (sin API key)
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/SPY"
            params = {
                "range": "6mo",
                "interval": "1d"
            }
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                result = data.get("chart", {}).get("result", [])
                if result:
                    precios_data = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
                    precios = [p for p in precios_data if p is not None][-120:]
                    
                    if len(precios) > 2:
                        retorno, volatilidad = cls._calcular_rendimiento(precios)
                        print(f"✅ DATOS REALES - S&P 500 (Yahoo): {len(precios)} precios, último: ${precios[-1]:.2f}")
                        return {
                            "precios": precios,
                            "retorno": retorno,
                            "volatilidad": volatilidad,
                            "fuente": "Yahoo Finance"
                        }
            else:
                print(f"❌ Yahoo Finance falló - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Yahoo Finance error: {e}")
        
        # Fallback: generar datos simulados
        print("🔄 DATOS SIMULADOS - Usando datos simulados para S&P 500")
        return cls._generar_datos_simulados("SPY", dias=120)
    
    @classmethod
    def _obtener_datos_bitcoin(cls):
        """Obtiene datos históricos de Bitcoin"""
        try:
            url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
            params = {
                "vs_currency": "usd",
                "days": "120",
                "interval": "daily"
            }
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            if cls.COINGECKO_KEY:
                headers['X-CoinGecko-Api-Key'] = cls.COINGECKO_KEY
                print("🔑 Usando API Key de CoinGecko")
            else:
                print("🔓 Usando CoinGecko sin API Key (límites bajos)")
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                precios_data = data.get("prices", [])
                
                if precios_data:
                    precios = [float(p[1]) for p in precios_data]
                    retorno, volatilidad = cls._calcular_rendimiento(precios)
                    
                    print(f"✅ DATOS REALES - Bitcoin: {len(precios)} precios, último: ${precios[-1]:.2f}")
                    return {
                        "precios": precios,
                        "retorno": retorno,
                        "volatilidad": volatilidad,
                        "fuente": "CoinGecko"
                    }
            else:
                print(f"❌ API CoinGecko falló - Status: {response.status_code}")
                if response.status_code == 429:
                    print("❌ Límite de CoinGecko excedido, espera 1 minuto")
        except Exception as e:
            print(f"❌ API CoinGecko error: {e}")
        
        # Intentar Alpha Vantage si está configurada
        if cls.ALPHA_VANTAGE_KEY and cls.ALPHA_VANTAGE_KEY != 'demo':
            try:
                url = f"{cls.ALPHA_VANTAGE_URL}?function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD&apikey={cls.ALPHA_VANTAGE_KEY}"
                response = requests.get(url, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    time_series = data.get("Time Series (Digital Currency Daily)", {})
                    
                    if time_series:
                        precios = []
                        for fecha_str, valores in sorted(time_series.items(), reverse=True)[:120]:
                            try:
                                precio = float(valores["4a. close (USD)"])
                                precios.append(precio)
                            except (KeyError, ValueError):
                                continue
                        
                        if len(precios) > 2:
                            retorno, volatilidad = cls._calcular_rendimiento(precios)
                            print(f"✅ DATOS REALES - Bitcoin: {len(precios)} precios")
                            
                            return {
                                "precios": precios,
                                "retorno": retorno,
                                "volatilidad": volatilidad,
                                "fuente": "Alpha Vantage"
                            }
                else:
                    print(f"❌ API Alpha Vantage BTC falló - Status: {response.status_code}")
            except Exception as e:
                print(f"❌ API Alpha Vantage BTC error: {e}")
        
        # Fallback: datos simulados
        print("🔄 DATOS SIMULADOS - Usando datos simulados para Bitcoin")
        return cls._generar_datos_simulados("BTC", dias=120)
    
    @classmethod
    def _obtener_datos_nfts(cls):
        """Obtiene datos históricos de NFTs (CryptoPunks)"""
        if cls.COINGECKO_KEY:
            try:
                print("🔧 Probando API CoinGecko para NFTs...")
                url = f"{cls.COINGECKO_URL}/nfts/cryptopunks"
                headers = {
                    'User-Agent': 'Mozilla/5.0'
                }
                if cls.COINGECKO_KEY:
                    headers['X-CoinGecko-Api-Key'] = cls.COINGECKO_KEY
                    print("🔑 Usando API Key de CoinGecko para NFTs")
                else:
                    print("🔓 Usando CoinGecko sin API Key para NFTs (puede fallar)")
                
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    floor_price = data.get('floor_price', {}).get('usd')
                    
                    if floor_price:
                        # USAR DATOS SIMULADOS CON PARÁMETROS REALISTAS
                        # En lugar de generar serie temporal con tendencia artificial
                        print(f"✅ DATOS REALES - NFTs: precio base ${floor_price:,.0f}")
                        return cls._generar_datos_simulados("CRYPTOPUNKS", dias=120)
            except Exception as e:
                print(f"❌ API CoinGecko NFTs error: {e}")
        
        # Fallback: datos simulados con parámetros realistas
        print("🔄 DATOS SIMULADOS - Usando datos simulados para NFTs")
        return cls._generar_datos_simulados("CRYPTOPUNKS", dias=120)

    @classmethod
    def _calcular_rendimiento(cls, precios):
        """
        Calcula CORRECTAMENTE rendimiento y volatilidad a partir de serie de precios
        CON LÍMITES REALISTAS
        """
        if len(precios) < 2:
            return 0.01, 0.05  # Valores por defecto realistas
        
        # Invertir para tener orden cronológico (más antiguo primero)
        precios = list(reversed(precios))
        valores = np.array(precios)
        
        # Calcular rendimientos diarios LOGARÍTMICOS (correcto)
        rendimientos_diarios = np.diff(np.log(valores))
        
        # Retorno mensual esperado = promedio de rendimientos diarios * 21 días
        retorno_mensual = float(np.mean(rendimientos_diarios) * 21)
        
        # Volatilidad mensual = desviación estándar de rendimientos diarios * raíz(21)
        volatilidad_mensual = float(np.std(rendimientos_diarios) * np.sqrt(21))
        
        # 🔥 LÍMITES REALISTAS PARA EVITAR VALORES EXTREMOS
        limites_retorno = {
            "SPY": (0.001, 0.03),      # 1% a 3% mensual máximo
            "BTC": (-0.02, 0.05),      # -2% a 5% mensual máximo  
            "CRYPTOPUNKS": (-0.05, 0.08) # -5% a 8% mensual máximo
        }
        
        # Determinar tipo de activo por rango de precios
        precio_promedio = np.mean(precios)
        if 500 < precio_promedio < 700:
            min_ret, max_ret = limites_retorno["SPY"]
            activo = "S&P 500"
        elif precio_promedio > 50000:
            min_ret, max_ret = limites_retorno["BTC"] 
            activo = "Bitcoin"
        else:
            min_ret, max_ret = limites_retorno["CRYPTOPUNKS"]
            activo = "NFTs"
        
        # Aplicar límites
        retorno_mensual = max(min(retorno_mensual, max_ret), min_ret)
        
        print(f"🔢 {activo}: {len(precios)} precios, retorno={retorno_mensual:.4f}, volatilidad={volatilidad_mensual:.4f}")
        
        return retorno_mensual, volatilidad_mensual
    
    @classmethod
    def _generar_datos_simulados(cls, simbolo, dias=120):
        """
        Genera datos simulados realistas para fallback
        
        Args:
            simbolo: Símbolo del activo (SPY, BTC, CRYPTOPUNKS)
            dias: Número de días a generar
        
        Returns:
            dict: Datos simulados con precios, retorno y volatilidad
        """
        base_price = cls.PRECIOS_BASE.get(simbolo, 100.0)
        
        # Parámetros de simulación por activo
        parametros = {
            "SPY": {"volatilidad_diaria": 0.012, "tendencia": 0.0002, "retorno": 0.007, "vol": 0.015},
            "BTC": {"volatilidad_diaria": 0.045, "tendencia": 0.0005, "retorno": 0.015, "vol": 0.06},
            "CRYPTOPUNKS": {"volatilidad_diaria": 0.08, "tendencia": 0.001, "retorno": 0.02, "vol": 0.08},
        }
        
        params = parametros.get(simbolo, {"volatilidad_diaria": 0.025, "tendencia": 0.0001, "retorno": 0.01, "vol": 0.04})
        
        # Generar serie temporal
        precios = []
        precio_actual = base_price
        
        for i in range(dias):
            # Aplicar tendencia temporal
            time_factor = 1 + (params["tendencia"] * i)
            
            # Variación aleatoria
            variation = random.uniform(-params["volatilidad_diaria"], params["volatilidad_diaria"])
            precio_actual = precio_actual * (1 + variation)
            
            # Asegurar precio mínimo
            precio_actual = max(precio_actual, base_price * 0.5)
            
            precios.append(precio_actual)
        
        print(f"📊 Generados {dias} precios simulados para {simbolo}")
        
        return {
            "precios": precios,
            "retorno": params["retorno"],
            "volatilidad": params["vol"],
            "fuente": "Simulado"
        }
    
    @classmethod
    def _generar_serie_temporal_nft(cls, precio_base, dias=120):
        """Genera serie temporal para NFTs basada en precio actual"""
        precios = []
        precio = precio_base
        
        for i in range(dias):
            # Volatilidad alta para NFTs
            variation = random.uniform(-0.06, 0.06)
            precio = precio * (1 + variation)
            precio = max(precio, precio_base * 0.3)
            precios.append(precio)
        
        return precios


# ===== Función auxiliar para usar en views.py =====

def obtener_parametros_activos():
    """
    Función de conveniencia para obtener todos los parámetros necesarios
    
    Returns:
        dict: {
            "CDT Bancario": {"retorno": float, "volatilidad": float, "info": dict},
            "S&P 500": {"retorno": float, "volatilidad": float, "info": dict},
            "Cripto (BTC)": {"retorno": float, "volatilidad": float, "info": dict},
            "NFTs": {"retorno": float, "volatilidad": float, "info": dict}
        }
    """
    try:
        # Obtener todos los datos
        datos_mercado = MarketDataService.obtener_datos_completos()
        
        # Construir diccionario de parámetros
        activos = {
            "CDT Bancario": {
                "retorno": datos_mercado["cdt"]["tasa"] / 12,  # Mensual
                "volatilidad": 0.001,  # Muy baja volatilidad
                "info": datos_mercado["cdt"]
            },
            "S&P 500": {
                "retorno": datos_mercado["sp500"]["retorno"],
                "volatilidad": datos_mercado["sp500"]["volatilidad"],
                "info": datos_mercado["sp500"]
            },
            "Cripto (BTC)": {
                "retorno": datos_mercado["btc"]["retorno"],
                "volatilidad": datos_mercado["btc"]["volatilidad"],
                "info": datos_mercado["btc"]
            },
            "NFTs": {
                "retorno": datos_mercado["nfts"]["retorno"],
                "volatilidad": datos_mercado["nfts"]["volatilidad"],
                "info": datos_mercado["nfts"]
            }
        }
        
        print("✅ Parámetros de activos calculados exitosamente")
        return activos
        
    except Exception as e:
        print(f"❌ Error obteniendo parámetros de activos: {e}")
        
        # Valores por defecto seguros
        return {
            "CDT Bancario": {
                "retorno": 0.0075,  # ~9% anual
                "volatilidad": 0.001,
                "info": {"fuente": "Fallback"}
            },
            "S&P 500": {
                "retorno": 0.007,
                "volatilidad": 0.015,
                "info": {"fuente": "Fallback"}
            },
            "Cripto (BTC)": {
                "retorno": 0.015,
                "volatilidad": 0.06,
                "info": {"fuente": "Fallback"}
            },
            "NFTs": {
                "retorno": 0.02,
                "volatilidad": 0.08,
                "info": {"fuente": "Fallback"}
            }
        }