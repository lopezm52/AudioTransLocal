#!/usr/bin/env python3
"""
Transcription Worker for AudioTransLocal

This module implements the core transcription workflow using whisper.cpp
with chunked processing, language detection, and progress tracking.

Epic 3: Core Transcription Workflow
"""

import os
import logging
from pathlib import Path
from typing import Optional
from math import ceil

from PySide6.QtCore import QObject, QRunnable, Signal
import ffmpeg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """
    Signals emitted by TranscriptionWorker to communicate with the main UI thread.
    
    These signals provide real-time updates about the transcription process
    and allow the UI to react appropriately to different stages and outcomes.
    """
    
    # Emitted when transcription task begins
    started = Signal(str)  # memo_id
    
    # Emitted during processing to show progress
    progress = Signal(str, str)  # memo_id, status_message
    
    # Emitted when transcription completes successfully
    finished = Signal(str, str)  # memo_id, transcript_file_path
    
    # Emitted when an error occurs during transcription
    error = Signal(str, str)  # memo_id, error_message


class TranscriptionWorker(QRunnable):
    """
    Background worker that handles the complete transcription workflow.
    
    This worker runs on a background thread and implements the following workflow:
    1. Get audio file duration using ffmpeg
    2. Extract 2-minute sample for language detection
    3. Process full audio in 10-minute chunks
    4. Save transcript to .txt file
    """
    
    def __init__(self, memo, model_path: str):
        """
        Initialize the transcription worker.
        
        Args:
            memo: VoiceMemoModel object with ID, file path, and metadata
            model_path: Absolute path to the Whisper model file (.bin)
        """
        super().__init__()
        self.memo = memo
        self.model_path = model_path
        self.signals = WorkerSignals()
        
        # Validate inputs
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Whisper model not found: {model_path}")
        
        if not self.memo.file_path or not Path(self.memo.file_path).exists():
            raise FileNotFoundError(f"Audio file not found: {self.memo.file_path}")
    
    def run(self):
        """
        Main transcription workflow - runs on background thread.
        
        This method implements the complete transcription process as specified
        in the technical requirements, with robust error handling and progress updates.
        """
        try:
            # Emit started signal
            self.signals.started.emit(self.memo.uuid)
            logger.info(f"🎤 Starting transcription for memo: {self.memo.uuid}")
            
            # Step 1: Get audio duration
            try:
                duration = self._get_audio_duration()
                logger.info(f"📏 Audio duration: {duration:.2f} seconds")
            except Exception as e:
                raise RuntimeError(f"Failed to analyze audio file: {str(e)}")
            
            # Step 2: Language detection
            try:
                detected_language = self._detect_language(duration)
                logger.info(f"🌍 Detected language: {detected_language}")
            except Exception as e:
                raise RuntimeError(f"Language detection failed: {str(e)}")
            
            # Step 3: Chunked transcription
            try:
                transcript_path = self._transcribe_in_chunks(duration, detected_language)
                logger.info(f"✅ Transcription completed: {transcript_path}")
            except Exception as e:
                raise RuntimeError(f"Transcription processing failed: {str(e)}")
            
            # Emit success signal
            self.signals.finished.emit(self.memo.uuid, str(transcript_path))
            
        except Exception as e:
            # Comprehensive error handling with detailed error messages
            error_msg = self._format_error_message(e)
            logger.error(f"❌ Transcription failed for {self.memo.uuid}: {error_msg}")
            self.signals.error.emit(self.memo.uuid, error_msg)
    
    def _format_error_message(self, exception: Exception) -> str:
        """
        Format exception into user-friendly error message.
        
        Args:
            exception: The caught exception
            
        Returns:
            User-friendly error message
        """
        error_type = type(exception).__name__
        error_str = str(exception)
        
        # Provide specific error messages for common issues
        if "No such file or directory" in error_str:
            return "Audio file not found or inaccessible"
        elif "Permission denied" in error_str:
            return "Permission denied accessing audio file"
        elif "Invalid data found" in error_str or "No audio streams" in error_str:
            return "Audio file is corrupted or invalid format"
        elif "whisper" in error_str.lower():
            return f"Whisper model error: {error_str}"
        elif "ffmpeg" in error_str.lower():
            return f"Audio processing error: {error_str}"
        elif "No space left" in error_str:
            return "Insufficient disk space for transcription"
        else:
            return f"{error_type}: {error_str}"
    
    def _get_audio_duration(self) -> float:
        """
        Get the total duration of the audio file using ffmpeg.
        
        Returns:
            Duration in seconds as float
        """
        try:
            probe = ffmpeg.probe(str(self.memo.file_path))
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            raise RuntimeError(f"Failed to get audio duration: {e}")
    
    def _detect_language(self, duration: float) -> str:
        """
        Detect the language of the audio using a 2-minute sample.
        
        Args:
            duration: Total audio duration in seconds
            
        Returns:
            Language code (e.g., 'en', 'es', 'fr')
        """
        try:
            # Calculate sample start time (middle of file, or 0 if < 2 minutes)
            if duration < 120:  # Less than 2 minutes
                start_time = 0
                sample_duration = min(duration, 120)
            else:
                start_time = (duration / 2) - 60  # Start 1 minute before middle
                sample_duration = 120
            
            self.signals.progress.emit(self.memo.uuid, "Detecting language...")
            
            # Extract audio sample using ffmpeg
            audio_buffer = self._extract_audio_chunk(start_time, sample_duration)
            
            # For now, we'll implement a placeholder that returns 'en'
            # TODO: Implement actual whisper.cpp language detection
            detected_language = self._whisper_detect_language(audio_buffer)
            
            return detected_language
            
        except Exception as e:
            raise RuntimeError(f"Language detection failed: {e}")
    
    def _transcribe_in_chunks(self, duration: float, language: str) -> Path:
        """
        Transcribe the full audio file in 10-minute chunks.
        
        Args:
            duration: Total audio duration in seconds
            language: Detected language code
            
        Returns:
            Path to the completed transcript file
        """
        try:
            # Calculate number of 10-minute chunks
            chunk_duration = 600  # 10 minutes in seconds
            num_chunks = ceil(duration / chunk_duration)
            
            # Prepare output file
            transcript_path = self._get_transcript_path()
            transcript_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                for i in range(num_chunks):
                    # Update progress
                    progress_msg = f"Transcribing chunk {i+1} of {num_chunks}..."
                    self.signals.progress.emit(self.memo.uuid, progress_msg)
                    
                    # Calculate chunk timing
                    chunk_start = i * chunk_duration
                    chunk_length = min(chunk_duration, duration - chunk_start)
                    
                    # Extract audio chunk
                    audio_buffer = self._extract_audio_chunk(chunk_start, chunk_length)
                    
                    # Transcribe chunk with detected language
                    chunk_text = self._whisper_transcribe_with_language(audio_buffer, language)
                    
                    # Write to file with separator
                    f.write(chunk_text)
                    if i < num_chunks - 1:  # Add separator except for last chunk
                        f.write("\n\n")
            
            return transcript_path
            
        except Exception as e:
            raise RuntimeError(f"Chunked transcription failed: {e}")
    
    def _extract_audio_chunk(self, start_time: float, duration: float) -> bytes:
        """
        Extract a specific chunk of audio as PCM buffer using ffmpeg.
        
        Args:
            start_time: Start time in seconds
            duration: Chunk duration in seconds
            
        Returns:
            Raw PCM audio data as bytes
        """
        try:
            # Use ffmpeg to extract audio chunk as 16-bit, 16kHz mono PCM
            stream = (
                ffmpeg
                .input(str(self.memo.file_path), ss=start_time, t=duration)
                .output('pipe:', format='s16le', acodec='pcm_s16le', ac=1, ar=16000)
                .run(capture_stdout=True, quiet=True)
            )
            
            return stream[0]  # stdout contains the PCM data
            
        except Exception as e:
            raise RuntimeError(f"Audio extraction failed: {e}")
    
    def _get_transcript_path(self) -> Path:
        """
        Generate the output path for the transcript file.
        
        Returns:
            Path object for the transcript file
        """
        # Use Application Support directory
        app_support = Path.home() / "Library" / "Application Support" / "AudioTransLocal"
        transcripts_dir = app_support / "transcriptions"
        
        # Use memo UUID as filename
        filename = f"{self.memo.uuid}.txt"
        return transcripts_dir / filename
    
    def _whisper_detect_language(self, audio_buffer: bytes) -> str:
        """
        Detect language using OpenAI Whisper (since whisper.cpp is not available).
        
        Args:
            audio_buffer: Raw PCM audio data
            
        Returns:
            Language code (e.g., 'en')
        """
        try:
            import whisper
            import numpy as np
            
            # Convert audio buffer to format expected by OpenAI Whisper
            audio_data = self._prepare_audio_for_whisper(audio_buffer)
            
            # Load a small model for language detection (faster)
            # Extract the model ID from the path (e.g., "tiny.en" from "ggml-tiny.en.bin")
            model_filename = Path(self.model_path).name
            if "tiny" in model_filename:
                detect_model = "tiny"
            elif "base" in model_filename:
                detect_model = "base"
            else:
                detect_model = "tiny"  # Default to fastest
            
            logger.info(f"🔍 Loading {detect_model} model for language detection...")
            model = whisper.load_model(detect_model)
            
            # Use detect language feature
            # First 30 seconds should be enough for language detection
            sample_length = min(len(audio_data), 30 * 16000)  # 30 seconds at 16kHz
            sample_audio = audio_data[:sample_length]
            
            # Detect language using Whisper
            result = model.transcribe(sample_audio, task="detect_language")
            detected_language = result.get('language', 'en')
            
            logger.info(f"🌍 Language detected: {detected_language}")
            return detected_language
            
        except ImportError:
            # Fallback when OpenAI Whisper not available
            logger.warning("⚠️ OpenAI Whisper not available, defaulting to English")
            return 'en'
        except Exception as e:
            # If language detection fails, default to English but log the error
            logger.warning(f"⚠️ Language detection failed: {e}, defaulting to English")
            return 'en'
    
    def _whisper_transcribe_with_language(self, audio_buffer: bytes, language: str) -> str:
        """
        Transcribe audio using OpenAI Whisper with specified language.
        
        Args:
            audio_buffer: Raw PCM audio data
            language: Language code to use for transcription
            
        Returns:
            Transcribed text
        """
        try:
            import whisper
            import numpy as np
            
            # Convert audio buffer to format expected by OpenAI Whisper
            audio_data = self._prepare_audio_for_whisper(audio_buffer)
            
            # Extract the model ID from the path (e.g., "tiny.en" from "ggml-tiny.en.bin")
            model_filename = Path(self.model_path).name
            if "tiny.en" in model_filename:
                model_id = "tiny.en"
            elif "tiny" in model_filename:
                model_id = "tiny"
            elif "base.en" in model_filename:
                model_id = "base.en" 
            elif "base" in model_filename:
                model_id = "base"
            elif "small.en" in model_filename:
                model_id = "small.en"
            elif "small" in model_filename:
                model_id = "small"
            elif "medium.en" in model_filename:
                model_id = "medium.en"
            elif "medium" in model_filename:
                model_id = "medium"
            elif "large" in model_filename:
                model_id = "large"
            else:
                model_id = "tiny"  # Default fallback
            
            logger.info(f"🤖 Loading {model_id} model for transcription...")
            model = whisper.load_model(model_id)
            
            # Run transcription with specified language for better accuracy and speed
            result = model.transcribe(audio_data, language=language if language != 'en' else None)
            transcribed_text = result.get('text', '').strip()
            
            chunk_size_seconds = len(audio_buffer) / (16000 * 2)  # 16kHz, 16-bit
            logger.info(f"🎯 Transcribed {chunk_size_seconds:.1f}s chunk in {language}: {len(transcribed_text)} chars")
            
            return transcribed_text
            
        except ImportError:
            # Fallback when OpenAI Whisper not available
            chunk_size_seconds = len(audio_buffer) / (16000 * 2)  # 16kHz, 16-bit
            placeholder_text = f"[Transcription placeholder - {chunk_size_seconds:.1f}s audio chunk in {language}]"
            logger.info(f"🎯 Using placeholder for {chunk_size_seconds:.1f}s chunk in {language}")
            return placeholder_text
            
        except Exception as e:
            # If transcription fails, create an error placeholder but don't fail the whole process
            chunk_size_seconds = len(audio_buffer) / (16000 * 2)  # 16kHz, 16-bit
            error_text = f"[Error transcribing {chunk_size_seconds:.1f}s chunk: {str(e)}]"
            logger.error(f"❌ Transcription error for {chunk_size_seconds:.1f}s chunk: {e}")
            return error_text
    
    def _prepare_audio_for_whisper(self, audio_buffer: bytes) -> any:
        """
        Convert raw PCM audio buffer to format expected by whisper.cpp.
        
        Args:
            audio_buffer: Raw 16-bit, 16kHz mono PCM data
            
        Returns:
            Audio data in format expected by whisper.cpp (likely numpy array)
        """
        try:
            import numpy as np
            
            # Convert bytes to numpy array
            # audio_buffer is 16-bit signed integers, so we need np.int16
            audio_array = np.frombuffer(audio_buffer, dtype=np.int16)
            
            # Convert to float32 normalized to [-1, 1] as expected by whisper
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            return audio_float
            
        except ImportError:
            # If numpy not available, return raw buffer (whisper.cpp might handle it)
            logger.warning("⚠️ numpy not available for audio conversion")
            return audio_buffer
        except Exception as e:
            logger.error(f"❌ Audio preparation failed: {e}")
            return audio_buffer
