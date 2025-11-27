"""
Servidor FastAPI con GraphQL y REST para VitalSync.
"""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from src.adapters.inbound.graphql.resolvers import schema, Context
from src.adapters.inbound.rest.routes import router as vitals_router
from src.adapters.outbound.persistance import (
    AsyncSessionLocal, init_db,
    UserRepositoryImpl, FamilyGroupRepositoryImpl, FamilyMemberRepositoryImpl,
    VitalRepositoryImpl, AlertRepositoryImpl, GroupCaregiverRepositoryImpl
)
from src.core.services import (
    UserService, FamilyGroupService, FamilyMemberService,
    VitalService, AlertService
)
from src.ml.services.prediction_service import HealthRiskPredictionService
from src.config.Settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos y el modelo ML al arrancar"""
    print("VitalSync - Iniciando...")
    print("  -> Inicializando base de datos...")
    await init_db()
    print("  -> Base de datos lista")
    print("  -> Cargando modelo ML de prediccion de riesgo...")
    # Pre-cargar el modelo ML para que este listo
    from src.ml.models.vital_risk_network import VitalRiskPredictor
    _ = VitalRiskPredictor()
    print("  -> Modelo ML cargado")
    print("VitalSync listo!")
    yield
    print("Cerrando VitalSync...")


def create_app() -> FastAPI:
    """Crea y configura la aplicación FastAPI"""
    app = FastAPI(
        title="VitalSync API",
        description="API GraphQL y REST para monitoreo de salud familiar",
        version="0.1.0",
        lifespan=lifespan
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En producción, especificar dominios
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST API para IoT (Node-RED)
    app.include_router(vitals_router)

    # GraphQL context
    async def get_context(request: Request) -> Context:
        """Crea el contexto con dependencias inyectadas"""
        # Obtener user_id del token JWT (simplificado)
        current_user_id: Optional[str] = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # TODO: Validar JWT real
            if token.startswith("jwt-token-for-"):
                current_user_id = token.replace("jwt-token-for-", "")

        # Crear sesión de DB
        async with AsyncSessionLocal() as session:
            # Crear repositorios
            user_repo = UserRepositoryImpl(session)
            family_group_repo = FamilyGroupRepositoryImpl(session)
            family_member_repo = FamilyMemberRepositoryImpl(session)
            vital_repo = VitalRepositoryImpl(session)
            alert_repo = AlertRepositoryImpl(session)
            group_caregiver_repo = GroupCaregiverRepositoryImpl(session)

            # Crear servicios
            user_service = UserService(user_repo)
            family_group_service = FamilyGroupService(family_group_repo, group_caregiver_repo)
            family_member_service = FamilyMemberService(family_member_repo, family_group_repo)
            vital_service = VitalService(vital_repo, family_member_repo, alert_repo)
            alert_service = AlertService(alert_repo)
            ml_service = HealthRiskPredictionService(vital_repo)

            return Context(
                user_service=user_service,
                family_group_service=family_group_service,
                family_member_service=family_member_service,
                vital_service=vital_service,
                alert_service=alert_service,
                ml_service=ml_service,
                current_user_id=current_user_id
            )

    # GraphQL router
    graphql_app = GraphQLRouter(
        schema,
        context_getter=get_context
    )

    app.include_router(graphql_app, prefix="/graphql")

    return app


# Instancia de la aplicación
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.adapters.inbound.graphql.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
