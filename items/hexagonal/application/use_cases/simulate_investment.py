from decimal import Decimal
from typing import Dict, Any
from ....services.market_service import obtener_parametros_activos  # ✅ CORREGIDO
from ...domain.entities.investment import InvestmentSimulation  # ✅ CORREGIDO

class SimulateInvestmentUseCase:  # ✅ NOMBRE CORREGIDO
    """Caso de uso que ORQUESTA la simulación - REUTILIZA tu código actual"""

    def execute(self, monto: float, meses: int) -> Dict[str, Any]:
        # 1. Obtener parámetros (usa tu función actual)
        activos = obtener_parametros_activos()  # ✅ CORREGIDO
        
        # 2. Crear entidad de dominio
        resultados = {}
        
        for nombre_activo, params in activos.items():  # ✅ CORREGIDO
            simulation = InvestmentSimulation(  # ✅ CORREGIDO
                monto=Decimal(str(monto)),
                meses=meses,
                asset_type=nombre_activo  # ✅ CORREGIDO
            )
            
            # 3. Usar lógica de dominio para cálculos
            resultado = simulation.calcular_crecimiento(
                retorno_mensual=Decimal(str(params["retorno"])),
                volatilidad=Decimal(str(params["volatilidad"]))
            )
            
            # ✅ CORREGIDA la estructura del diccionario
            resultados[nombre_activo] = {
                **resultado,  # Desempaqueta el resultado del cálculo
                "recomendacion": params.get("recomendacion", ""),
                "retorno_mensual": round(params["retorno"] * 100, 4),
                "volatilidad_mensual": round(params["volatilidad"] * 100, 4)
            }
        
        return resultados