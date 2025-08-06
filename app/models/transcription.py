"""
Transcription state management using Finite State Machine

This module provides a robust state machine for managing transcription
workflow states, preventing invalid state transitions and providing
clear status tracking.
"""

from enum import Enum, auto
from typing import Dict, Set, Optional
from dataclasses import dataclass
from datetime import datetime


class TranscriptionState(Enum):
    """
    Finite State Machine states for transcription workflow.
    
    Each state represents a distinct phase in the transcription process.
    """
    READY = auto()              # Initial state, ready to start
    PREPARING = auto()          # Loading model, preparing resources
    DETECTING_LANGUAGE = auto() # Auto-detecting audio language
    TRANSCRIBING = auto()       # Active transcription in progress
    POST_PROCESSING = auto()    # Cleaning up transcript, applying filters
    COMPLETED = auto()          # Successfully completed
    FAILED = auto()            # Failed with error
    CANCELLED = auto()         # User cancelled the operation

    def __str__(self) -> str:
        """Human-readable state names"""
        state_names = {
            self.READY: "Ready",
            self.PREPARING: "Preparing",
            self.DETECTING_LANGUAGE: "Detecting Language",
            self.TRANSCRIBING: "Transcribing",
            self.POST_PROCESSING: "Post-processing",
            self.COMPLETED: "Completed",
            self.FAILED: "Failed",
            self.CANCELLED: "Cancelled"
        }
        return state_names.get(self, self.name)


@dataclass
class TranscriptionProgress:
    """
    Data structure for transcription progress information.
    """
    state: TranscriptionState
    percentage: int = 0
    current_chunk: int = 0
    total_chunks: int = 0
    estimated_time_remaining: Optional[float] = None  # seconds
    message: str = ""
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class TranscriptionStateMachine:
    """
    Finite State Machine for managing transcription workflow.
    
    Ensures only valid state transitions are allowed and provides
    clear progress tracking throughout the transcription process.
    """
    
    # Define valid state transitions
    VALID_TRANSITIONS: Dict[TranscriptionState, Set[TranscriptionState]] = {
        TranscriptionState.READY: {
            TranscriptionState.PREPARING,
            TranscriptionState.CANCELLED
        },
        TranscriptionState.PREPARING: {
            TranscriptionState.DETECTING_LANGUAGE,
            TranscriptionState.TRANSCRIBING,  # Skip language detection
            TranscriptionState.FAILED,
            TranscriptionState.CANCELLED
        },
        TranscriptionState.DETECTING_LANGUAGE: {
            TranscriptionState.TRANSCRIBING,
            TranscriptionState.FAILED,
            TranscriptionState.CANCELLED
        },
        TranscriptionState.TRANSCRIBING: {
            TranscriptionState.POST_PROCESSING,
            TranscriptionState.COMPLETED,  # Skip post-processing
            TranscriptionState.FAILED,
            TranscriptionState.CANCELLED
        },
        TranscriptionState.POST_PROCESSING: {
            TranscriptionState.COMPLETED,
            TranscriptionState.FAILED,
            TranscriptionState.CANCELLED
        },
        TranscriptionState.COMPLETED: {
            TranscriptionState.READY  # Allow restart
        },
        TranscriptionState.FAILED: {
            TranscriptionState.READY  # Allow retry
        },
        TranscriptionState.CANCELLED: {
            TranscriptionState.READY  # Allow restart
        }
    }

    def __init__(self, initial_state: TranscriptionState = TranscriptionState.READY):
        """
        Initialize the state machine.
        
        Args:
            initial_state: Starting state for the machine
        """
        self._current_state = initial_state
        self._progress = TranscriptionProgress(state=initial_state)
        self._state_history: list[TranscriptionProgress] = [self._progress]

    @property
    def current_state(self) -> TranscriptionState:
        """Get the current state."""
        return self._current_state

    @property
    def progress(self) -> TranscriptionProgress:
        """Get the current progress information."""
        return self._progress

    @property
    def is_active(self) -> bool:
        """Check if transcription is currently in progress."""
        active_states = {
            TranscriptionState.PREPARING,
            TranscriptionState.DETECTING_LANGUAGE,
            TranscriptionState.TRANSCRIBING,
            TranscriptionState.POST_PROCESSING
        }
        return self._current_state in active_states

    @property
    def is_terminal(self) -> bool:
        """Check if the current state is terminal (completed, failed, or cancelled)."""
        terminal_states = {
            TranscriptionState.COMPLETED,
            TranscriptionState.FAILED,
            TranscriptionState.CANCELLED
        }
        return self._current_state in terminal_states

    def can_transition_to(self, new_state: TranscriptionState) -> bool:
        """
        Check if transition to new state is valid.
        
        Args:
            new_state: Target state to transition to
            
        Returns:
            True if transition is valid, False otherwise
        """
        valid_states = self.VALID_TRANSITIONS.get(self._current_state, set())
        return new_state in valid_states

    def transition_to(self, new_state: TranscriptionState, 
                     percentage: int = 0, 
                     message: str = "",
                     current_chunk: int = 0,
                     total_chunks: int = 0,
                     estimated_time_remaining: Optional[float] = None) -> bool:
        """
        Transition to a new state with progress information.
        
        Args:
            new_state: Target state to transition to
            percentage: Progress percentage (0-100)
            message: Status message
            current_chunk: Current processing chunk
            total_chunks: Total number of chunks
            estimated_time_remaining: Estimated time remaining in seconds
            
        Returns:
            True if transition was successful, False if invalid
            
        Raises:
            ValueError: If transition is not allowed
        """
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid transition from {self._current_state} to {new_state}. "
                f"Valid transitions: {self.VALID_TRANSITIONS.get(self._current_state, set())}"
            )

        # Update state and progress
        self._current_state = new_state
        self._progress = TranscriptionProgress(
            state=new_state,
            percentage=max(0, min(100, percentage)),  # Clamp to 0-100
            current_chunk=current_chunk,
            total_chunks=total_chunks,
            estimated_time_remaining=estimated_time_remaining,
            message=message
        )
        
        # Add to history
        self._state_history.append(self._progress)
        
        return True

    def reset(self):
        """Reset the state machine to READY state."""
        self._current_state = TranscriptionState.READY
        self._progress = TranscriptionProgress(state=TranscriptionState.READY)
        self._state_history = [self._progress]

    def get_state_history(self) -> list[TranscriptionProgress]:
        """Get the complete state transition history."""
        return self._state_history.copy()

    def get_progress_percentage(self) -> int:
        """Get the current progress percentage."""
        return self._progress.percentage

    def get_status_message(self) -> str:
        """Get a human-readable status message."""
        if self._progress.message:
            return self._progress.message
        
        # Default messages based on state
        default_messages = {
            TranscriptionState.READY: "Ready to start transcription",
            TranscriptionState.PREPARING: "Preparing transcription resources...",
            TranscriptionState.DETECTING_LANGUAGE: "Detecting audio language...",
            TranscriptionState.TRANSCRIBING: f"Transcribing audio... ({self._progress.percentage}%)",
            TranscriptionState.POST_PROCESSING: "Processing transcript...",
            TranscriptionState.COMPLETED: "Transcription completed successfully",
            TranscriptionState.FAILED: "Transcription failed",
            TranscriptionState.CANCELLED: "Transcription cancelled"
        }
        
        return default_messages.get(self._current_state, str(self._current_state))
