class MarketDataAdapter:
    """Adaptador que envuelve tu market_service actual"""
    
    def __init__(self):
        from .....services.market_service import obtener_parametros_activos
        self.obtener_parametros_activos = obtener_parametros_activos
    
    def get_asset_parameters(self) -> dict:
        """Interface uniforme para obtener parámetros"""
        return self.obtener_parametros_activos()