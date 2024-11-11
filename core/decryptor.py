"""
GAMDL Core Decryptor Module

Provides advanced decryption capabilities for various media formats
with support for multiple DRM and encryption schemes.
"""

import base64
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pywidevine
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from gamdl.core import logger
from gamdl.constants import SecurityConstants
from gamdl.config import config

class EncryptionAlgorithm(Enum):
    """
    Supported encryption algorithms
    """
    AES_128_CBC = auto()
    AES_256_CBC = auto()
    WIDEVINE = auto()
    FAIRPLAY = auto()
    PLAYREADY = auto()

@dataclass
class DecryptionContext:
    """
    Comprehensive decryption context and metadata
    """
    source_path: Path
    destination_path: Path
    encryption_type: EncryptionAlgorithm
    key: Optional[str] = None
    iv: Optional[str] = None
    pssh: Optional[str] = None  # Protection System Specific Header
    metadata: Dict[str, Any] = field(default_factory=dict)
    decryption_status: bool = False
    error_message: Optional[str] = None

class BaseDecryptor(ABC):
    """
    Abstract base class for media decryption
    """
    @abstractmethod
    def decrypt(self, context: DecryptionContext) -> DecryptionContext:
        """
        Abstract method for decryption
        
        Args:
            context (DecryptionContext): Decryption context
        
        Returns:
            DecryptionContext: Updated decryption context
        """
        pass

class AESDecryptor(BaseDecryptor):
    """
    AES-based decryption implementation
    """
    def decrypt(self, context: DecryptionContext) -> DecryptionContext:
        """
        Decrypt file using AES algorithm
        
        Args:
            context (DecryptionContext): Decryption context
        
        Returns:
            DecryptionContext: Updated decryption context
        """
        try:
            # Validate required parameters
            if not all([context.key, context.iv]):
                raise ValueError("AES decryption requires key and IV")
            
            key = base64.b64decode(context.key)
            iv = base64.b64decode(context.iv)
            
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            with open(context.source_path, 'rb') as f_in, \
                 open(context.destination_path, 'wb') as f_out:
                
                while True:
                    chunk = f_in.read(8192)
                    if not chunk:
                        break
                    
                    decrypted_chunk = cipher.decrypt(chunk)
                    
                    # Remove padding for last chunk
                    if len(chunk) < 8192:
                        decrypted_chunk = unpad(decrypted_chunk, AES.block_size)
                    
                    f_out.write(decrypted_chunk)
            
            context.decryption_status = True
            return context
        
        except Exception as e:
            context.decryption_status = False
            context.error_message = str(e)
            logger.error(f"AES Decryption failed: {e}")
            return context

class WidevineCDMDecryptor(BaseDecryptor):
    """
    Widevine Content Decryption Module (CDM) decryptor
    """
    def __init__(self, device_path: Optional[Path] = None):
        """
        Initialize Widevine CDM
        
        Args:
            device_path (Optional[Path]): Path to Widevine device file
        """
        self.device_path = device_path or config.get('widevine.device_path')
        self.cdm = self._initialize_cdm()
    
    def _initialize_cdm(self):
        """
        Initialize Widevine CDM
        
        Returns:
            Widevine CDM instance
        """
        try:
            device = pywidevine.Device.load(self.device_path)
            return pywidevine.Cdm.from_device(device)
        except Exception as e:
            logger.critical(f"Widevine CDM initialization failed: {e}")
            raise

    def decrypt(self, context: DecryptionContext) -> DecryptionContext:
        """
        Decrypt using Widevine CDM
        
        Args:
            context (DecryptionContext): Decryption context
        
        Returns:
            DecryptionContext: Updated decryption context
        """
        try:
            if not context.pssh:
                raise ValueError("PSSH is required for Widevine decryption")
            
            # Create PSSH object
            pssh_obj = pywidevine.PSSH(context.pssh)
            
            # Open CDM session
            session = self.cdm.open()
            
            # Generate license challenge
            challenge = base64.b64encode(
                self.cdm.get_license_challenge(session, pssh_obj)
            ).decode()
            
            # TODO: Implement license retrieval logic
            # This would typically involve calling a license server
            license_response = self._retrieve_license(challenge)
            
            # Parse license
            self.cdm.parse_license(session, license_response)
            
            # Get decryption key
            decryption_key = next(
                key.key.hex() 
                for key in self.cdm.get_keys(session) 
                if key.type == 'CONTENT'
            )
            
            context.key = decryption_key
            context.decryption_status = True
            
            return context
        
        except Exception as e:
            context.decryption_status = False
            context.error_message = str(e)
            logger.error(f"Widevine decryption failed: {e}")
            return context
    
    def _retrieve_license(self, challenge: str) -> str:
        """
        Retrieve license from license server
        
        Args:
            challenge (str): License challenge
        
        Returns:
            str: License response
        """
        # TODO: Implement actual license retrieval
        # This is a placeholder and should be replaced with actual implementation
        raise NotImplementedError("License retrieval not implemented")

class DecryptionManager:
    """
    Centralized decryption management
    """
    def __init__(self):
        self.decryptors = {
            EncryptionAlgorithm.AES_128_CBC: AESDecryptor(),
            EncryptionAlgorithm.AES_256_CBC: AESDecryptor(),
            EncryptionAlgorithm.WIDEVINE: WidevineCDMDecryptor()
        }
    
    def decrypt(self, context: DecryptionContext) -> DecryptionContext:
        """
        Decrypt using appropriate decryptor
        
        Args:
            context (DecryptionContext): Decryption context
        
        Returns:
            DecryptionContext: Updated decryption context
        """
        try:
            decryptor = self.decryptors.get(context.encryption_type)
            
            if not decryptor:
                raise ValueError(f"No decryptor found for {context.encryption_type}")
            
            return decryptor.decrypt(context)
        
        except Exception as e:
            context.decryption_status = False
            context.error_message = str(e)
            logger.error(f"Decryption failed: {e}")
            return context
    
    def add_decryptor(
        self, 
        encryption_type: EncryptionAlgorithm, 
        decryptor: BaseDecryptor
    ):
        """ Add a custom decryptor to the manager
        
        Args:
            encryption_type (EncryptionAlgorithm): The encryption type for the decryptor
            decryptor (BaseDecryptor): An instance of the decryptor to add
        """
        self.decryptors[encryption_type] = decryptor

# Create singleton decryption manager
decryption_manager = DecryptionManager()

# Expose key components
__all__ = [
    'DecryptionContext',
    'BaseDecryptor',
    'AESDecryptor',
    'WidevineCDMDecryptor',
    'DecryptionManager',
    'decryption_manager',
    'EncryptionAlgorithm'
          ]
