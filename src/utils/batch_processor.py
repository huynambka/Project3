"""Batch processor for collecting and processing HTTP messages."""

import logging
import threading
from typing import List, Dict, Any, Callable, Optional
from queue import Queue
from ..config import Settings

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Collects HTTP messages and processes them in batches."""

    def __init__(
        self,
        settings: Settings,
        process_callback: Callable[[List[Dict[str, str]]], None],
    ):
        """Initialize batch processor.

        Args:
            settings: Application settings
            process_callback: Function to call with completed batch
        """
        self.settings = settings
        self.batch_size = settings.batch_size
        self.process_callback = process_callback

        self.queue: Queue = Queue()
        self.current_batch: List[Dict[str, str]] = []
        self.lock = threading.Lock()
        self.message_count = 0

        logger.info(
            f"Batch processor initialized with batch size: {self.batch_size}"
        )

    def add_message(
        self, request: str, response: str, timestamp: str = ""
    ) -> Dict[str, Any]:
        """Add a message to the batch queue.

        Args:
            request: Raw HTTP request string
            response: Raw HTTP response string
            timestamp: Message timestamp

        Returns:
            Dict with status and batch info
        """
        with self.lock:
            message = {
                "request": request,
                "response": response,
                "timestamp": timestamp,
            }

            self.current_batch.append(message)
            self.message_count += 1

            batch_position = len(self.current_batch)
            logger.info(
                f"Message added to batch: {batch_position}/{self.batch_size}"
            )

            # Check if batch is complete
            if len(self.current_batch) >= self.batch_size:
                logger.info(
                    f"Batch complete ({self.batch_size} messages), processing..."
                )
                batch_to_process = self.current_batch.copy()
                self.current_batch = []

                # Process batch in background thread
                thread = threading.Thread(
                    target=self._process_batch_async,
                    args=(batch_to_process,),
                    daemon=True,
                )
                thread.start()

                return {
                    "status": "batch_complete",
                    "message": f"Batch of {self.batch_size} messages sent for processing",
                    "batch_position": self.batch_size,
                    "batch_size": self.batch_size,
                    "total_messages": self.message_count,
                }

            return {
                "status": "queued",
                "message": f"Message queued ({batch_position}/{self.batch_size})",
                "batch_position": batch_position,
                "batch_size": self.batch_size,
                "total_messages": self.message_count,
            }

    def _process_batch_async(self, batch: List[Dict[str, str]]) -> None:
        """Process a batch asynchronously."""
        try:
            logger.info(f"Processing batch of {len(batch)} messages")
            self.process_callback(batch)
            logger.info("Batch processing complete")
        except Exception as e:
            logger.error(f"Error processing batch: {e}", exc_info=True)

    def flush(self) -> Optional[int]:
        """Force process current batch even if not full.

        Returns:
            Number of messages in flushed batch, or None if batch was empty
        """
        with self.lock:
            if not self.current_batch:
                logger.info("No messages to flush")
                return None

            batch_size = len(self.current_batch)
            logger.info(f"Flushing incomplete batch ({batch_size} messages)")
            batch_to_process = self.current_batch.copy()
            self.current_batch = []

            # Process batch in background thread
            thread = threading.Thread(
                target=self._process_batch_async,
                args=(batch_to_process,),
                daemon=True,
            )
            thread.start()

            return batch_size

    def get_status(self) -> Dict[str, Any]:
        """Get current batch processor status."""
        with self.lock:
            return {
                "current_batch_size": len(self.current_batch),
                "batch_size_limit": self.batch_size,
                "total_messages_received": self.message_count,
                "batches_processed": self.message_count // self.batch_size,
            }
