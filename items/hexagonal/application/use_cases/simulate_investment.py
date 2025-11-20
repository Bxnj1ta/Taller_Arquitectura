from decimal import Decimal
from typing import Dict, Any
from ....services.market_service import obtener_parametros_activos  # ✅ CORREGIDO
from ...domain.entities.investment import InvestmentSimulation  # ✅ CORREGIDO

class SimulateInvestmentUseCase:
    def execute_with_existing_data(self, monto: float, meses: int, activos: dict) -> Dict[str, Any]:
        """Ejecuta simulación CON datos ya obtenidos"""
        resultados = {}
        
        for nombre_activo, params in activos.items():
            simulation = InvestmentSimulation(
                monto=Decimal(str(monto)),
                meses=meses,
                asset_type=nombre_activo
            )
            
            resultado = simulation.calcular_crecimiento(
                retorno_mensual=Decimal(str(params["retorno"])),
                volatilidad=Decimal(str(params["volatilidad"]))
            )
            
            # ✅ AGREGAR RECOMENDACIÓN ESPECÍFICA
            recomendacion = self._generar_recomendacion(
                nombre_activo, 
                resultado["ganancia_porcentaje"],
                meses,
                params["volatilidad"]
            )
            
            resultados[nombre_activo] = {
                **resultado,
                "recomendacion": recomendacion,  # ← Nueva recomendación
                "retorno_mensual": round(params["retorno"] * 100, 4),
                "volatilidad_mensual": round(params["volatilidad"] * 100, 4)
            }
        
        return resultados
    
    def _generar_recomendacion(self, activo: str, ganancia_porcentaje: float, meses: int, volatilidad: float) -> str:
        """Genera recomendación personalizada según el activo y perfil de riesgo"""
        
        recomendaciones = {
            # 📈 **CDT BANCARIO** - Conservador
            "CDT Bancario": [
                "💼 Ideal para preservar capital. Bajo riesgo, retorno estable garantizado.",
                "🛡️ Perfecto para fondos de emergencia o objetivos a corto plazo.",
                "📊 Recomendado para inversores conservadores que priorizan seguridad.",
                "⏱️ Excelente para plazos fijos sin exposición a volatilidad de mercado."
            ],
            
            # 📊 **S&P 500** - Moderado
            "S&P 500": [
                "🌎 Diversificación global en las 500 empresas más grandes de EE.UU.",
                "📈 Exposición al crecimiento económico estadounidense a largo plazo.",
                "💡 Ideal para acumulación de patrimonio con horizonte > 5 años.",
                "⚖️ Balance entre riesgo y retorno, histórico de crecimiento consistente."
            ],
            
            # ₿ **CRIPTO (BTC)** - Agresivo
            "Cripto (BTC)": [
                "🚀 Alto potencial de crecimiento pero volatilidad extrema.",
                "⚠️ Solo asignar capital que estés dispuesto a perder completamente.",
                "🔄 Considerar estrategia de Dollar-Cost Averaging para reducir riesgo.",
                "🌙 Exposición a tecnología blockchain y activos digitales emergentes."
            ],
            
            # 🎨 **NFTs** - Especulativo
            "NFTs": [
                "🎯 Mercado altamente especulativo con potencial alto pero riesgo extremo.",
                "🔍 Requiere conocimiento profundo del ecosistema y artistas específicos.",
                "💧 Baja liquidez - puede ser difícil vender rápidamente sin pérdidas.",
                "🖼️ Más adecuado para coleccionistas que para inversores tradicionales."
            ]
        }
        
        # Lógica para seleccionar recomendación basada en métricas
        if activo in recomendaciones:
            opciones = recomendaciones[activo]
            
            # Seleccionar basado en perfil de riesgo
            if activo == "CDT Bancario":
                return opciones[0]  # Siempre conservador
            elif activo == "S&P 500":
                if meses >= 60:  # Largo plazo
                    return opciones[1]
                else:  # Mediano plazo
                    return opciones[2]
            elif activo == "Cripto (BTC)":
                if volatilidad > 0.1:  # Alta volatilidad
                    return opciones[1]  # Advertencia de riesgo
                else:
                    return opciones[0]  # Potencial crecimiento
            elif activo == "NFTs":
                return opciones[0]  # Siempre especulativo
            
        return "💼 Considera diversificar tu portafolio según tu perfil de riesgo."