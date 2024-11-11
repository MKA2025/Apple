"""
GAMDL Core Remuxer Module

Provides advanced media remuxing capabilities with support for various
multimedia containers and track manipulation.
"""

import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

import ffmpeg

from gamdl.core import logger
from gamdl.constants import (
    MediaType,
    RemuxerConstants,
    FileConstants
)
from gamdl.config import config

class RemuxerMode(Enum):
    """Remuxing modes supported"""
    FFMPEG = auto()
    MP4BOX = auto()
    HANDBRAKE = auto()

class TrackType(Enum):
    """Media track types"""
    VIDEO = auto()
    AUDIO = auto()
    SUBTITLE = auto()
    CHAPTER = auto()

@dataclass
class MediaTrack:
    """Represents a media track with comprehensive metadata"""
    track_id: str
    track_type: TrackType
    codec: str
    language: str = 'und'
    bitrate: Optional[int] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RemuxContext:
    """Comprehensive remuxing context"""
    input_files: List[Path]
    output_file: Path
    media_type: MediaType
    tracks: List[MediaTrack] = field(default_factory=list)
    mode: RemuxerMode = RemuxerMode.FFMPEG
    tags: Dict[str, str] = field(default_factory=dict)
    additional_options: Dict[str, Any] = field(default_factory=dict)
    remux_status: bool = False
    error_message: Optional[str] = None

class BaseRemuxer:
    """Base abstract class for media remuxing"""
    
    @classmethod
    def validate_input(cls, context: RemuxContext) -> bool:
        """
        Validate input files and remux context
        
        Args:
            context (RemuxContext): Remuxing context
        
        Returns:
            bool: Whether inputs are valid
        """
        # Check input file existence
        for input_file in context.input_files:
            if not input_file.exists():
                logger.error(f"Input file not found: {input_file}")
                return False
        
        # Check output directory permissions
        try:
            context.output_file.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.error(f"No write permission for {context.output_file.parent}")
            return False
        
        return True

class FFmpegRemuxer(BaseRemuxer):
    """FFmpeg-based remuxer"""
    
    @classmethod
    def remux(cls, context: RemuxContext) -> RemuxContext:
        """
        Remux media using FFmpeg
        
        Args:
            context (RemuxContext): Remuxing context
        
        Returns:
            RemuxContext: Updated remuxing context
        """
        if not cls.validate_input(context):
            context.remux_status = False
            context.error_message = "Invalid input files"
            return context
        
        try:
            # Prepare FFmpeg input streams
            input_streams = [ffmpeg.input(str(input_file)) for input_file in context.input_files]
            
            # Merge input streams
            merged_stream = ffmpeg.merge_outputs(*input_streams)
            
            # Add metadata
            if context.tags:
                merged_stream = merged_stream.global_args('-metadata', *[
                    f'{k}={v}' for k, v in context.tags.items()
                ])
            
            # Add additional FFmpeg options
            if context.additional_options:
                for option, value in context.additional_options.items():
                    merged_stream = merged_stream.global_args(option, str(value))
            
            # Output configuration
            output_options = {
                'c': 'copy',  # Copy streams without re-encoding
                'movflags': '+faststart',  # Optimize for web streaming
            }
            
            # Execute FFmpeg
            ffmpeg.output(
                merged_stream, 
                str(context.output_file), 
                **output_options
            ).overwrite_output().run(capture_stdout=True, capture_stderr=True)
            
            context.remux_status = True
            return context
        
        except ffmpeg.Error as e:
            context.remux_status = False
            context.error_message = f"FFmpeg Error: {e.stderr.decode()}"
            logger.error(context.error_message)
            return context
        except Exception as e:
            context.remux_status = False
            context.error_message = str(e)
            logger.error(f"Remuxing failed: {e}")
            return context

class MP4BoxRemuxer(BaseRemuxer):
    """MP4Box-based remuxer"""
    
    @classmethod
    def remux(cls, context: RemuxContext) -> RemuxContext:
        """
        Remux media using MP4Box
        
        Args:
            context (RemuxContext): Remuxing context
        
        Returns:
            RemuxContext: Updated remuxing context
        """
        if not cls.validate_input(context):
            context.remux_status = False
            context.error_message = "Invalid input files"
            return context
        
        try:
            # Prepare MP4Box command
            cmd = [
                config.get('mp4box_path', 'MP4Box'),
                '-quiet',
                '-new', str(context.output_file)
            ]
            
            # Add input files
            for input_file in context.input_files:
                cmd.extend(['-add', str(input_file)])
            
            # Add tags
            if context.tags:
                for key, value in context.tags.items():
                    cmd.extend(['-itags', f'{key}={value}'])
            
            # Run MP4Box
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            context.remux_status = True
            return context
        
        except subprocess.CalledProcessError as e:
            context.remux_status = False
            context.error_message = f"MP4Box Error: {e.stderr}"
            logger.error(context.error_message)
            return context
        except Exception as e:
            context.remux_status = False
            context.error_message = str(e)
            logger.error(f"Remuxing failed: {e}")
            return context

class RemuxerManager:
    """
    Centralized remuxing management with multi-mode support
    """
    
    def __init__(self):
        self.remuxers = {
            RemuxerMode.FFMPEG: FFmpegRemuxer,
            RemuxerMode.MP4BOX: MP4BoxRemuxer
        }
    
    def remux(self, context: RemuxContext) -> RemuxContext:
        """
        Remux media using the specified mode
        
        Args:
            context (RemuxContext): Remuxing context
        
        Returns:
            RemuxContext: Updated remuxing context
        """
        try:
            remuxer = self.remuxers.get(context.mode)
            
            if not remuxer:
                raise ValueError(f"No remuxer found for mode {context.mode}")
            
            return remuxer.remux(context)
        
        except Exception as e:
            context.remux_status = False
            context.error_message = str(e)
            logger.error(f"Remuxing failed: {e}")
            return context
    
    def add_remuxer(
        self, 
        mode: RemuxerMode, 
        remuxer_class: type
    ):
        """
        Add a custom remuxer to the manager
        
        Args:
            mode (RemuxerMode): The remuxing mode for the remuxer
            remuxer_class (type): A class of the remuxer to add
        """
        self.remuxers[mode] = remuxer_class

# Create singleton remuxer manager
remuxer_manager = RemuxerManager()

# Expose key components
__all__ = [
    'RemuxContext',
    'BaseRemuxer',
    'FFmpegRemuxer',
    'MP4BoxRemuxer',
    'RemuxerManager',
    'remuxer_manager',
    'RemuxerMode',
    'TrackType',
    'MediaTrack'
]
