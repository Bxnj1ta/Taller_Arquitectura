class Plugin:
    def name(self):
        return "PremiumPlan"

    def init(self, ctx):
        self.ctx = ctx
        print("[PremiumPlan] Inicializado")

    def execute(self, action, *args, **kwargs):
        if action == "consultar_precio":
            return "Precio actual: $100 (tiempo real)"
        elif action == "historial":
            return "Historial: 5 años de datos disponibles"
        elif action == "alerta":
            return "Alerta configurada en tiempo real 🚀"
        else:
            return "Funcionalidad desconocida en PremiumPlan"

    def shutdown(self):
        print("[PremiumPlan] apagado")