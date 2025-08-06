#!/usr/bin/env python3
"""
Service Container for Dependency Injection

This module provides a robust dependency injection container that manages
service registration and singleton lifecycle, replacing manual service
creation with a declarative registration approach.
"""

from typing import Dict, Any, Callable, TypeVar, Type
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceContainer:
    """
    A true Dependency Injection container that manages service registration 
    and singleton lifecycle.
    
    This replaces the manual ServiceFactory approach with a more scalable
    registration-based system where services are defined declaratively.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._recipes: Dict[str, Callable[[], Any]] = {}
        self._creating: set[str] = set()  # Circular dependency detection

    def register(self, name: str, recipe: Callable[[], Any]) -> 'ServiceContainer':
        """
        Register a service recipe for lazy instantiation.
        
        Args:
            name: Service identifier
            recipe: Factory function that creates the service instance
            
        Returns:
            Self for method chaining
        """
        if name in self._recipes:
            logger.warning(f"Service '{name}' is being re-registered")
        
        self._recipes[name] = recipe
        return self

    def register_singleton(self, name: str, instance: Any) -> 'ServiceContainer':
        """
        Register a pre-created singleton instance.
        
        Args:
            name: Service identifier
            instance: The service instance
            
        Returns:
            Self for method chaining
        """
        self._services[name] = instance
        return self

    def get(self, name: str) -> Any:
        """
        Get a service instance. Services are created as singletons on first request.
        
        Args:
            name: Service identifier
            
        Returns:
            The service instance
            
        Raises:
            ValueError: If service is not registered
            RuntimeError: If circular dependency is detected
        """
        # Return existing instance if available
        if name in self._services:
            return self._services[name]
        
        # Check if service is registered
        if name not in self._recipes:
            available_services = list(self._recipes.keys())
            raise ValueError(
                f"Service '{name}' not registered. "
                f"Available services: {available_services}"
            )
        
        # Detect circular dependencies
        if name in self._creating:
            cycle = " -> ".join(self._creating) + f" -> {name}"
            raise RuntimeError(f"Circular dependency detected: {cycle}")
        
        try:
            # Mark as being created
            self._creating.add(name)
            
            # Create the service instance using its recipe
            logger.debug(f"Creating service: {name}")
            self._services[name] = self._recipes[name]()
            logger.debug(f"Service created successfully: {name}")
            
            return self._services[name]
            
        finally:
            # Always remove from creating set
            self._creating.discard(name)

    def has(self, name: str) -> bool:
        """
        Check if a service is registered.
        
        Args:
            name: Service identifier
            
        Returns:
            True if service is registered
        """
        return name in self._recipes or name in self._services

    def clear(self):
        """Clear all registered services and instances."""
        self._services.clear()
        self._recipes.clear()
        self._creating.clear()

    def get_registered_services(self) -> list[str]:
        """Get list of all registered service names."""
        return list(self._recipes.keys()) + list(self._services.keys())


def create_container() -> ServiceContainer:
    """
    Creates and configures the main DI container with all application services.
    
    This function centralizes all dependency wiring in one place, making it
    easy to understand the application's service dependencies.
    
    Returns:
        Fully configured ServiceContainer
    """
    from pathlib import Path
    from app.services.credentials_manager import CredentialsManager
    from app.services.whisper_model_manager import WhisperModelManager
    from app.services.voice_memo_parser import VoiceMemoParser
    from app.services.transcription_service import TranscriptionService
    
    container = ServiceContainer()

    # Register core services
    container.register("credentials_manager", lambda: CredentialsManager())
    
    container.register("whisper_model_manager", lambda: WhisperModelManager())
    
    # Voice memo parser with default macOS location
    container.register("voice_memo_parser", lambda: VoiceMemoParser(
        voice_memos_folder=Path.home() / "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
    ))
    
    # Transcription service with dependencies
    container.register("transcription_service", lambda: TranscriptionService(
        whisper_model_manager=container.get("whisper_model_manager")
    ))
    
    logger.info(f"Service container configured with services: {container.get_registered_services()}")
    
    return container


# Legacy compatibility - maintain backward compatibility
class ServiceFactory:
    """
    Legacy ServiceFactory wrapper for backward compatibility.
    
    This maintains the existing interface while delegating to the new
    ServiceContainer internally.
    """
    
    def __init__(self):
        self._container = create_container()
    
    def get_credentials_manager(self):
        """Get credentials manager service."""
        return self._container.get("credentials_manager")
    
    def get_whisper_model_manager(self):
        """Get whisper model manager service."""
        return self._container.get("whisper_model_manager")
    
    def get_voice_memo_parser(self):
        """Get voice memo parser service."""
        return self._container.get("voice_memo_parser")
    
    def get_transcription_service(self):
        """Get transcription service."""
        return self._container.get("transcription_service")
    
    @property
    def container(self) -> ServiceContainer:
        """Access the underlying container for advanced usage."""
        return self._container
