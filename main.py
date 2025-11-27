"""
VitalSync - Plataforma de Monitoreo de Salud Familiar
Entry point de la aplicación.
"""
import uvicorn
from src.config.Settings import settings


def main():
    """Inicia el servidor VitalSync"""
    print("🏥 Iniciando VitalSync API...")
    print(f"   Host: {settings.HOST}")
    print(f"   Port: {settings.PORT}")
    print(f"   Debug: {settings.DEBUG}")
    print(f"   GraphQL: http://{settings.HOST}:{settings.PORT}/graphql")

    uvicorn.run(
        "src.adapters.inbound.graphql.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )


if __name__ == "__main__":
    main()
