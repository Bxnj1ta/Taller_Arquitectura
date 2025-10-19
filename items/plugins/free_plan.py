class Plugin:
    def name(self):
        return "FreePlan"

    def init(self, ctx):
        self.ctx = ctx
        print("[FreePlan] Inicializado")

    def execute(self, action, *args, **kwargs):
        if action == "consultar_precio":
            return "Precio actual: $100 (limitado)"
        elif action == "historial":
            return "Historial: Solo 7 días disponibles en plan gratuito"
        else:
            return "Funcionalidad no disponible en FreePlan"

    def shutdown(self):
        print("[FreePlan] apagado")