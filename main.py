"""
VitalSync - Plataforma de Monitoreo de Salud Familiar
Entry point de la aplicación.
"""
import uvicorn
from pathlib import Path
from src.config.Settings import settings


def main():
    """Inicia el servidor VitalSync"""
    print("=" * 60)
    print("  VitalSync - Plataforma de Monitoreo de Salud Familiar")
    print("=" * 60)
    print(f"   Host: {settings.HOST}")
    print(f"   Port: {settings.PORT}")
    print(f"   Debug: {settings.DEBUG}")
    print(f"   GraphQL: http://{settings.HOST}:{settings.PORT}/graphql")
    print(f"   REST API: http://{settings.HOST}:{settings.PORT}/api")

    # Verificar modelo ML
    model_path = Path("models/vital_risk_best.pt")
    if model_path.exists():
        size_kb = model_path.stat().st_size / 1024
        print(f"   ML Model: {model_path} ({size_kb:.1f} KB)")
    else:
        print("   ML Model: No entrenado (ejecutar: uv run python scripts/train_model.py)")

    print("=" * 60)

    uvicorn.run(
        "src.adapters.inbound.graphql.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )


if __name__ == "__main__":
    main()
