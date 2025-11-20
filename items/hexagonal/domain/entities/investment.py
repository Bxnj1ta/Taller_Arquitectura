from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Any

@dataclass
class InvestmentSimulation:
    """Entidad de dominio para simulaciones - COMPLEMENTA tus modelos Django"""
    monto: Decimal
    meses: int
    asset_type: str
    resultado_esperado: Decimal = None
    mejor_escenario: Decimal = None
    peor_escenario: Decimal = None
    
    def calcular_crecimiento(self, retorno_mensual: Decimal, volatilidad: Decimal) -> Dict[str, Any]:
        """Lógica de negocio pura para cálculos"""
        # 1. ESCENARIO ESPERADO
        esperado = self.monto * ((1 + retorno_mensual) ** self.meses)
        
        # 2. MEJOR CASO (controlado)
        mejor_retorno = retorno_mensual + (volatilidad * Decimal('0.5'))
        mejor = self.monto * ((1 + mejor_retorno) ** self.meses)
        
        # 3. PEOR CASO (controlado)  
        peor_retorno = retorno_mensual - (volatilidad * Decimal('0.5'))
        peor_retorno = max(peor_retorno, Decimal('-0.2'))  # Límite -20% mensual
        peor = self.monto * ((1 + peor_retorno) ** self.meses)
        
        return {
            "esperado": round(esperado, 2),
            "mejor": round(mejor, 2),
            "peor": round(peor, 2),
            "ganancia": round(esperado - self.monto, 2),
            "ganancia_porcentaje": round(((esperado - self.monto) / self.monto * 100), 2)
        }