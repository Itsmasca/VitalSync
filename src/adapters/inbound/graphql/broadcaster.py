"""
Event broadcaster para GraphQL Subscriptions.
Maneja la distribución de eventos en tiempo real usando asyncio.
"""
import asyncio
from typing import AsyncGenerator, Dict, Set, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class EventType(Enum):
    VITAL_UPDATED = "vital_updated"
    ALERT_CREATED = "alert_created"
    MEMBER_STATUS_CHANGED = "member_status_changed"


@dataclass
class Event:
    type: EventType
    payload: Any
    member_id: str
    family_id: str | None = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class EventBroadcaster:
    """
    Broadcaster de eventos para subscriptions GraphQL.
    Usa asyncio.Queue para cada subscriber.
    """

    def __init__(self):
        # Dict de queues por tipo de evento y filtro
        self._vital_subscribers: Dict[str, Set[asyncio.Queue]] = {}  # member_id -> queues
        self._alert_subscribers: Dict[str, Set[asyncio.Queue]] = {}  # family_id -> queues
        self._status_subscribers: Dict[str, Set[asyncio.Queue]] = {}  # member_id -> queues
        self._global_subscribers: Set[asyncio.Queue] = set()  # Sin filtro

    async def subscribe_vitals(
        self, member_id: str | None = None
    ) -> AsyncGenerator[Event, None]:
        """
        Suscribe a actualizaciones de signos vitales.
        Si member_id es None, recibe todos los vitales.
        """
        queue: asyncio.Queue = asyncio.Queue()

        if member_id:
            if member_id not in self._vital_subscribers:
                self._vital_subscribers[member_id] = set()
            self._vital_subscribers[member_id].add(queue)
        else:
            self._global_subscribers.add(queue)

        try:
            while True:
                event = await queue.get()
                if event is None:  # Signal to stop
                    break
                yield event
        finally:
            # Cleanup
            if member_id and member_id in self._vital_subscribers:
                self._vital_subscribers[member_id].discard(queue)
                if not self._vital_subscribers[member_id]:
                    del self._vital_subscribers[member_id]
            else:
                self._global_subscribers.discard(queue)

    async def subscribe_alerts(
        self, family_id: str | None = None
    ) -> AsyncGenerator[Event, None]:
        """
        Suscribe a nuevas alertas.
        Si family_id es None, recibe todas las alertas.
        """
        queue: asyncio.Queue = asyncio.Queue()

        if family_id:
            if family_id not in self._alert_subscribers:
                self._alert_subscribers[family_id] = set()
            self._alert_subscribers[family_id].add(queue)
        else:
            self._global_subscribers.add(queue)

        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            if family_id and family_id in self._alert_subscribers:
                self._alert_subscribers[family_id].discard(queue)
                if not self._alert_subscribers[family_id]:
                    del self._alert_subscribers[family_id]
            else:
                self._global_subscribers.discard(queue)

    async def subscribe_member_status(
        self, member_id: str
    ) -> AsyncGenerator[Event, None]:
        """
        Suscribe a cambios de estado de un miembro específico.
        """
        queue: asyncio.Queue = asyncio.Queue()

        if member_id not in self._status_subscribers:
            self._status_subscribers[member_id] = set()
        self._status_subscribers[member_id].add(queue)

        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            if member_id in self._status_subscribers:
                self._status_subscribers[member_id].discard(queue)
                if not self._status_subscribers[member_id]:
                    del self._status_subscribers[member_id]

    async def publish_vital(self, vital_data: Any, member_id: str, family_id: str = None):
        """Publica un nuevo evento de signos vitales."""
        event = Event(
            type=EventType.VITAL_UPDATED,
            payload=vital_data,
            member_id=member_id,
            family_id=family_id
        )

        # Enviar a subscribers específicos del member
        if member_id in self._vital_subscribers:
            for queue in self._vital_subscribers[member_id]:
                await queue.put(event)

        # Enviar a subscribers globales
        for queue in self._global_subscribers:
            await queue.put(event)

    async def publish_alert(self, alert_data: Any, member_id: str, family_id: str = None):
        """Publica un nuevo evento de alerta."""
        event = Event(
            type=EventType.ALERT_CREATED,
            payload=alert_data,
            member_id=member_id,
            family_id=family_id
        )

        # Enviar a subscribers de la familia
        if family_id and family_id in self._alert_subscribers:
            for queue in self._alert_subscribers[family_id]:
                await queue.put(event)

        # Enviar a subscribers globales
        for queue in self._global_subscribers:
            await queue.put(event)

    async def publish_status_change(self, status_data: Any, member_id: str):
        """Publica un cambio de estado de miembro."""
        event = Event(
            type=EventType.MEMBER_STATUS_CHANGED,
            payload=status_data,
            member_id=member_id
        )

        if member_id in self._status_subscribers:
            for queue in self._status_subscribers[member_id]:
                await queue.put(event)

    def get_stats(self) -> dict:
        """Retorna estadísticas de subscribers activos."""
        return {
            "vital_subscribers": sum(len(q) for q in self._vital_subscribers.values()),
            "alert_subscribers": sum(len(q) for q in self._alert_subscribers.values()),
            "status_subscribers": sum(len(q) for q in self._status_subscribers.values()),
            "global_subscribers": len(self._global_subscribers)
        }


# Singleton global
broadcaster = EventBroadcaster()
