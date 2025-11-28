"""
Servidor FastAPI con GraphQL y REST para VitalSync.
Incluye soporte para WebSockets (GraphQL Subscriptions).
"""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from strawberry.extensions import SchemaExtension

from src.adapters.inbound.graphql.resolvers import Query, Mutation, Subscription
import strawberry
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
from src.config.Settings import settings


class SessionCleanupExtension(SchemaExtension):
    """Extensión para cerrar la sesión de DB después de cada request GraphQL"""

    async def on_request_end(self):
        context = self.execution_context.context
        if context and "db_session" in context:
            session = context["db_session"]
            await session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar"""
    await init_db()
    yield


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

    # GraphQL context - returns a dictionary
    async def get_context(request: Request) -> dict:
        """Crea el contexto con dependencias inyectadas"""
        from src.core.services.auth_service import auth_service

        # Obtener user_id del token JWT
        current_user_id: Optional[str] = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = auth_service.verify_token(token)
            if payload:
                current_user_id = payload.get("sub")

        # Crear sesión de DB (se mantiene abierta durante la request)
        session = AsyncSessionLocal()

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

        return {
            "user_service": user_service,
            "family_group_service": family_group_service,
            "family_member_service": family_member_service,
            "vital_service": vital_service,
            "alert_service": alert_service,
            "current_user_id": current_user_id,
            "db_session": session  # Para cerrar después si es necesario
        }

    # Schema con extensión para limpiar sesiones
    schema_with_cleanup = strawberry.Schema(
        query=Query,
        mutation=Mutation,
        subscription=Subscription,
        extensions=[SessionCleanupExtension]
    )

    # GraphQL router
    graphql_app = GraphQLRouter(
        schema_with_cleanup,
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
