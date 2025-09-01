import boto3
import json

class LambdaService:
    def __init__(self, region_name="us-east-1"):
        self.client = boto3.client("lambda", region_name=region_name)

    def invoke(self, function_name: str, payload: dict):
        response = self.client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        # Validación API10
        if "StatusCode" not in response or response["StatusCode"] != 200:
            raise ValueError("Error en Lambda")

        raw_payload = response["Payload"].read()
        data = json.loads(raw_payload)

        if not isinstance(data, dict) or "resultado" not in data:
            raise ValueError("Respuesta inesperada de Lambda")

        return data
