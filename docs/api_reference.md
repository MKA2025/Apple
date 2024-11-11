# Gamdl API Reference

## Table of Contents
- [Overview](#overview)
- [Core Modules](#core-modules)
- [Authentication](#authentication)
- [Download Managers](#download-managers)
- [Metadata Handlers](#metadata-handlers)
- [Exceptions](#exceptions)
- [Configuration](#configuration)
- [Utility Functions](#utility-functions)

## Overview

Gamdl provides a comprehensive API for music downloading and management across multiple platforms.

## Core Modules

### `gamdl.core`

#### Main Classes

```python
class GamdlCore:
    """
    Primary interface for Gamdl functionality
    """
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Gamdl core with optional configuration
        
        Args:
            config (Dict[str, Any], optional): Configuration dictionary
        """
    
    def download(self, url: str, **kwargs) -> DownloadResult:
        """
        Download music from a given URL
        
        Args:
            url (str): URL of track/playlist/album
            **kwargs: Additional download options
        
        Returns:
            DownloadResult: Download operation result
        """
    
    def get_metadata(self, url: str) -> Metadata:
        """
        Retrieve metadata for a given URL
        
        Args:
            url (str): URL of track/playlist/album
        
        Returns:
            Metadata: Extracted metadata object
        """
