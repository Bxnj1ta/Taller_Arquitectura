
# Inyección de dependencias: permite pasar cliente boto3 y json desde fuera (útil para pruebas y desacoplamiento)
import boto3
import json

class LambdaService:
    def __init__(self, client=None, json_module=None):
        """
        client: instancia de boto3.client('lambda') o mock para pruebas
        json_module: módulo json (por defecto el estándar)
        """
        self.client = client or boto3.client("lambda", region_name="us-east-1")
        self.json = json_module or json

    def invoke(self, function_name: str, payload: dict):
        response = self.client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=self.json.dumps(payload),
        )

        # Validación API10
        if "StatusCode" not in response or response["StatusCode"] != 200:
            raise ValueError("Error en Lambda")

        raw_payload = response["Payload"].read()
        data = self.json.loads(raw_payload)

        if not isinstance(data, dict) or "resultado" not in data:
            raise ValueError("Respuesta inesperada de Lambda")

        return data
