"""
Main entry point for GAMDL Telegram Bot

This module initializes and runs the Telegram bot with various services
and configurations.
"""

import sys
import asyncio
import logging
from typing import Optional

import click
from dotenv import load_dotenv

# Local imports
from gamdl import (
    __version__,
    PROJECT_ROOT,
    CONFIG_DIR,
    DOWNLOAD_DIR,
    logger
)
from gamdl.telegram.bot import GamdlTelegramBot
from gamdl.services.download_service import DownloadService
from gamdl.services.file_cleanup_service import FileCleanupService
from gamdl.services.notification_service import NotificationService
from gamdl.apis.apple_music import AppleMusicAPI
from gamdl.core.config import load_config

# Load environment variables
load_dotenv(PROJECT_ROOT / '.env')

class GamdlCLI:
    def __init__(self):
        self.config = load_config()
        self.logger = logging.getLogger(__name__)

    async def _initialize_services(self):
        """
        Initialize core services for the application
        
        Returns:
            dict: Initialized services
        """
        try:
            # Initialize Apple Music API
            apple_music_api = AppleMusicAPI(
                cookies_path=self.config.get('apple_music', {}).get('cookies_path')
            )

            # Initialize File Cleanup Service
            file_cleanup_service = FileCleanupService(
                download_dir=DOWNLOAD_DIR,
                max_file_age_hours=self.config.get('file_management', {}).get('max_file_age_hours', 24)
            )

            # Initialize Download Service
            download_service = DownloadService(
                apple_music_api=apple_music_api,
                file_cleanup_service=file_cleanup_service
            )

            # Initialize Notification Service
            notification_service = NotificationService()

            return {
                'apple_music_api': apple_music_api,
                'file_cleanup_service': file_cleanup_service,
                'download_service': download_service,
                'notification_service': notification_service
            }
        
        except Exception as e:
            self.logger.error(f"Service initialization failed: {e}")
            raise

    async def start_bot(self, debug: bool = False):
        """
        Start the Telegram Bot
        
        Args:
            debug (bool): Enable debug mode
        """
        try:
            # Set logging level based on debug flag
            logging.getLogger().setLevel(
                logging.DEBUG if debug else logging.INFO
            )

            # Initialize services
            services = await self._initialize_services()

            # Create Telegram Bot instance
            bot = GamdlTelegramBot(
                token=self.config.get('telegram', {}).get('bot_token'),
                services=services,
                debug=debug
            )

            # Start bot with periodic tasks
            await bot.start()

        except Exception as e:
            self.logger.critical(f"Bot startup failed: {e}")
            sys.exit(1)

    def run_cleanup(self):
        """
        Manually trigger file cleanup
        """
        file_cleanup_service = FileCleanupService(
            download_dir=DOWNLOAD_DIR
        )
        file_cleanup_service.cleanup_old_files()
        self.logger.info("Manual file cleanup completed")

@click.group()
@click.version_option(version=__version__)
def cli():
    """
    GAMDL Telegram Bot CLI
    
    Manage and run the Apple Music Downloader Telegram Bot
    """
    pass

@cli.command()
@click.option('--debug/--no-debug', default=False, help='Enable debug mode')
def start(debug: bool):
    """
    Start the Telegram Bot
    """
    cli_handler = GamdlCLI()
    
    try:
        asyncio.run(cli_handler.start_bot(debug=debug))
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

@cli.command()
def cleanup():
    """
    Manually trigger file cleanup
    """
    cli_handler = GamdlCLI()
    cli_handler.run_cleanup()

@cli.command()
@click.argument('url', required=True)
@click.option('--output', '-o', help='Custom output directory')
def download(url: str, output: Optional[str] = None):
    """
    Download a single track/album from Apple Music
    """
    cli_handler = GamdlCLI()
    
    try:
        download_service = cli_handler._initialize_services()['download_service']
        result = download_service.download(url, output_dir=output)
        
        if result:
            click.echo(f"Download successful: {result}")
        else:
            click.echo("Download failed")
    
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)

@cli.command()
def config_wizard():
    """
    Interactive configuration wizard
    """
    click.echo("🧙 GAMDL Configuration Wizard")
    # Implement interactive config setup
    pass

def main():
    """
    Main entry point for the application
    """
    try:
        cli()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
