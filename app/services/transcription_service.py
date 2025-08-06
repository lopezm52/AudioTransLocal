"""
Transcription service for AudioTransLocal

This service handles the core transcription functionality using OpenAI Whisper.
It provides a clean interface for transcribing audio files with progress tracking.
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any

from PySide6.QtCore import QObject, Signal, QThread

try:
    import whisper
    import torch
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("Warning: Whisper dependencies not available. Transcription will be disabled.")


@dataclass
class TranscriptionProgress:
    """Data class for transcription progress updates"""
    percentage: int
    status: str
    current_step: str


@dataclass
class TranscriptionResult:
    """Data class for transcription results"""
    success: bool
    text: str
    language: Optional[str] = None
    error_message: Optional[str] = None
    duration: Optional[float] = None


class WhisperTranscriptionWorker(QThread):
    """Worker thread for performing Whisper transcription"""
    
    # Signals
    progress_updated = Signal(TranscriptionProgress)
    transcription_completed = Signal(TranscriptionResult)
    
    def __init__(self, audio_file_path: str, model_path: str, model_id: str):
        super().__init__()
        self.audio_file_path = audio_file_path
        self.model_path = model_path
        self.model_id = model_id
        self.should_stop = False
        
    def run(self):
        """Run the transcription in a background thread"""
        if not WHISPER_AVAILABLE:
            result = TranscriptionResult(
                success=False,
                text="",
                error_message="Whisper dependencies are not installed. Please install torch and openai-whisper."
            )
            self.transcription_completed.emit(result)
            return
            
        try:
            start_time = time.time()
            
            # Update progress: Loading model
            self.progress_updated.emit(TranscriptionProgress(
                percentage=10,
                status="Loading AI model...",
                current_step="model_loading"
            ))
            
            if self.should_stop:
                return
            
            # Load the model
            if os.path.exists(self.model_path):
                model = whisper.load_model(self.model_path)
            else:
                # Fallback to downloading the model
                model = whisper.load_model(self.model_id)
            
            # Update progress: Processing audio
            self.progress_updated.emit(TranscriptionProgress(
                percentage=30,
                status="Processing audio file...",
                current_step="audio_processing"
            ))
            
            if self.should_stop:
                return
            
            # Update progress: Transcribing
            self.progress_updated.emit(TranscriptionProgress(
                percentage=50,
                status="Transcribing audio...",
                current_step="transcription"
            ))
            
            # Perform transcription
            result = model.transcribe(self.audio_file_path)
            
            if self.should_stop:
                return
            
            # Update progress: Finalizing
            self.progress_updated.emit(TranscriptionProgress(
                percentage=90,
                status="Finalizing transcription...",
                current_step="finalizing"
            ))
            
            # Extract results
            transcribed_text = result.get('text', '').strip()
            detected_language = result.get('language', None)
            
            duration = time.time() - start_time
            
            # Complete
            self.progress_updated.emit(TranscriptionProgress(
                percentage=100,
                status="Transcription completed!",
                current_step="completed"
            ))
            
            # Emit final result
            final_result = TranscriptionResult(
                success=True,
                text=transcribed_text,
                language=detected_language,
                duration=duration
            )
            self.transcription_completed.emit(final_result)
            
        except Exception as e:
            error_result = TranscriptionResult(
                success=False,
                text="",
                error_message=f"Transcription failed: {str(e)}"
            )
            self.transcription_completed.emit(error_result)
    
    def stop_transcription(self):
        """Stop the transcription process"""
        self.should_stop = True


class TranscriptionService(QObject):
    """Main transcription service"""
    
    # Signals
    transcription_started = Signal(str)  # file_path
    transcription_progress_updated = Signal(TranscriptionProgress)
    transcription_completed = Signal(str, TranscriptionResult)  # file_path, result
    
    def __init__(self, whisper_model_manager):
        super().__init__()
        self.whisper_model_manager = whisper_model_manager
        self.current_worker = None
        
    def is_transcription_running(self):
        """Check if a transcription is currently running"""
        return self.current_worker is not None and self.current_worker.isRunning()
    
    def start_transcription(self, audio_file_path: str):
        """Start transcribing an audio file"""
        if self.is_transcription_running():
            print("Transcription already in progress")
            return False
        
        # Get the selected model
        selected_model_id = self.whisper_model_manager.get_selected_model()
        if not selected_model_id:
            result = TranscriptionResult(
                success=False,
                text="",
                error_message="No Whisper model selected. Please select a model in Preferences."
            )
            self.transcription_completed.emit(audio_file_path, result)
            return False
        
        # Check if model is downloaded
        if not self.whisper_model_manager.is_model_downloaded(selected_model_id):
            result = TranscriptionResult(
                success=False,
                text="",
                error_message=f"Model '{selected_model_id}' is not downloaded. Please download it in Preferences."
            )
            self.transcription_completed.emit(audio_file_path, result)
            return False
        
        # Get model path
        model_path = self.whisper_model_manager.get_model_path(selected_model_id)
        
        # Create and start worker
        self.current_worker = WhisperTranscriptionWorker(
            audio_file_path=audio_file_path,
            model_path=model_path,
            model_id=selected_model_id
        )
        
        # Connect signals
        self.current_worker.progress_updated.connect(self.transcription_progress_updated.emit)
        self.current_worker.transcription_completed.connect(
            lambda result: self._on_transcription_completed(audio_file_path, result)
        )
        
        # Start transcription
        self.current_worker.start()
        self.transcription_started.emit(audio_file_path)
        
        return True
    
    def cancel_transcription(self):
        """Cancel the current transcription"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.stop_transcription()
            self.current_worker.wait(3000)  # Wait up to 3 seconds
            self.current_worker = None
    
    def _on_transcription_completed(self, file_path: str, result: TranscriptionResult):
        """Handle transcription completion"""
        self.transcription_completed.emit(file_path, result)
        self.current_worker = None
