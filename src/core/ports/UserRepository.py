from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.domain.UserModel import User, UserRole


class UserRepository(ABC):
    """
    Puerto (interface) que define el contrato para la persistencia de usuarios.

    Esta abstracción permite que el dominio no dependa de ninguna implementación
    específica de base de datos, siguiendo el principio de inversión de dependencias.

    Las implementaciones concretas (adapters) deben estar en:
    src/adapters/outbound/persistance/
    """

    @abstractmethod
    async def save(self, user: User) -> User:
        """
        Persiste un nuevo usuario.

        Args:
            user: Entidad de usuario a guardar

        Returns:
            Usuario guardado con ID asignado

        Raises:
            UserAlreadyExistsException: Si ya existe un usuario con el mismo email
        """
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """
        Actualiza un usuario existente.

        Args:
            user: Entidad de usuario con los datos actualizados

        Returns:
            Usuario actualizado

        Raises:
            UserNotFoundException: Si el usuario no existe
        """
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """
        Elimina un usuario por su ID.

        Args:
            user_id: ID del usuario a eliminar

        Returns:
            True si se eliminó correctamente

        Raises:
            UserNotFoundException: Si el usuario no existe
        """
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Obtiene un usuario por su ID.

        Args:
            user_id: ID del usuario

        Returns:
            Usuario encontrado o None si no existe
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Obtiene un usuario por su email.

        Args:
            email: Email del usuario

        Returns:
            Usuario encontrado o None si no existe
        """
        pass

    @abstractmethod
    async def get_by_device_id(self, device_id: str) -> Optional[User]:
        """
        Obtiene un usuario por su device_id vinculado.

        Args:
            device_id: ID del dispositivo

        Returns:
            Usuario encontrado o None si no existe
        """
        pass

    @abstractmethod
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        """
        Obtiene todos los usuarios con paginación.

        Args:
            limit: Número máximo de resultados
            offset: Número de resultados a saltar

        Returns:
            Lista de usuarios
        """
        pass

    @abstractmethod
    async def get_by_role(self, role: UserRole) -> List[User]:
        """
        Obtiene todos los usuarios con un rol específico.

        Args:
            role: Rol a filtrar

        Returns:
            Lista de usuarios con ese rol
        """
        pass

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """
        Verifica si existe un usuario con el email dado.

        Args:
            email: Email a verificar

        Returns:
            True si existe, False en caso contrario
        """
        pass

    @abstractmethod
    async def count(self) -> int:
        """
        Cuenta el total de usuarios.

        Returns:
            Numero total de usuarios
        """
        pass
