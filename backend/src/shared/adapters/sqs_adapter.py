"""
SQS adapter - AWS SQS queue operations.

Provides:
- Message sending to queues
- Message receiving and deletion
- Job payload serialization
"""

import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from ...config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class QueueMessage:
    """Received SQS message."""

    message_id: str
    receipt_handle: str
    body: Dict[str, Any]
    attributes: Dict[str, str]


class SQSAdapter:
    """
    Adapter for AWS SQS operations.

    Handles:
    - Sending messages to processing queues
    - Receiving messages for workers
    - Message deletion after processing
    """

    def __init__(
        self,
        region: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """
        Initialize SQS adapter.

        Args:
            region: AWS region
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
        """
        self.region = region or settings.AWS_REGION
        self.aws_access_key_id = aws_access_key_id or settings.AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY
        self._client = None

    @property
    def client(self):
        """Lazy-loaded SQS client."""
        if self._client is None:
            if self.aws_access_key_id and self.aws_secret_access_key:
                self._client = boto3.client(
                    "sqs",
                    region_name=self.region,
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                )
            else:
                # Use default credentials (IAM role, environment, etc.)
                self._client = boto3.client("sqs", region_name=self.region)
        return self._client

    def send_message(
        self,
        queue_url: str,
        message_body: Dict[str, Any],
        delay_seconds: int = 0,
        message_attributes: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Send a message to an SQS queue.

        Args:
            queue_url: URL of the queue
            message_body: Message payload (will be JSON serialized)
            delay_seconds: Delay before message becomes available
            message_attributes: Optional message attributes

        Returns:
            Message ID
        """
        try:
            params = {
                "QueueUrl": queue_url,
                "MessageBody": json.dumps(message_body),
                "DelaySeconds": delay_seconds,
            }

            if message_attributes:
                params["MessageAttributes"] = {
                    k: {"StringValue": str(v), "DataType": "String"}
                    for k, v in message_attributes.items()
                }

            response = self.client.send_message(**params)
            message_id = response["MessageId"]

            logger.info(f"Sent message {message_id} to {queue_url}")
            return message_id

        except ClientError as e:
            logger.error(f"Failed to send message to {queue_url}: {e}")
            raise

    def send_content_processing_job(
        self,
        shared_content_id: str,
        url: str,
    ) -> str:
        """
        Send a content processing job to the queue.

        Args:
            shared_content_id: SharedContent ID to process
            url: Content URL

        Returns:
            Message ID
        """
        message_body = {
            "job_type": "ingest_content",
            "shared_content_id": shared_content_id,
            "url": url,
        }

        return self.send_message(
            queue_url=settings.SQS_CONTENT_QUEUE_URL,
            message_body=message_body,
        )

    def send_clustering_job(
        self,
        user_id: str,
        content_category: Optional[str] = None,
    ) -> str:
        """
        Send a clustering job to the queue.

        Args:
            user_id: User ID to cluster
            content_category: Optional specific category to cluster

        Returns:
            Message ID
        """
        message_body = {
            "job_type": "cluster_user",
            "user_id": user_id,
        }

        if content_category:
            message_body["content_category"] = content_category

        return self.send_message(
            queue_url=settings.SQS_CLUSTERING_QUEUE_URL,
            message_body=message_body,
        )

    def receive_messages(
        self,
        queue_url: str,
        max_messages: int = 10,
        wait_time_seconds: int = 20,
        visibility_timeout: int = 300,
    ) -> List[QueueMessage]:
        """
        Receive messages from an SQS queue.

        Args:
            queue_url: URL of the queue
            max_messages: Maximum messages to receive (1-10)
            wait_time_seconds: Long polling wait time
            visibility_timeout: Time message is hidden from other consumers

        Returns:
            List of QueueMessage objects
        """
        try:
            response = self.client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=wait_time_seconds,
                VisibilityTimeout=visibility_timeout,
                MessageAttributeNames=["All"],
                AttributeNames=["All"],
            )

            messages = []
            for msg in response.get("Messages", []):
                try:
                    body = json.loads(msg["Body"])
                except json.JSONDecodeError:
                    body = {"raw": msg["Body"]}

                messages.append(
                    QueueMessage(
                        message_id=msg["MessageId"],
                        receipt_handle=msg["ReceiptHandle"],
                        body=body,
                        attributes=msg.get("Attributes", {}),
                    )
                )

            return messages

        except ClientError as e:
            logger.error(f"Failed to receive messages from {queue_url}: {e}")
            raise

    def delete_message(
        self,
        queue_url: str,
        receipt_handle: str,
    ) -> None:
        """
        Delete a message from the queue.

        Call this after successfully processing a message.

        Args:
            queue_url: URL of the queue
            receipt_handle: Receipt handle from received message
        """
        try:
            self.client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle,
            )
            logger.debug(f"Deleted message from {queue_url}")

        except ClientError as e:
            logger.error(f"Failed to delete message: {e}")
            raise

    def change_message_visibility(
        self,
        queue_url: str,
        receipt_handle: str,
        visibility_timeout: int,
    ) -> None:
        """
        Change visibility timeout for a message.

        Use this to extend processing time for long-running jobs.

        Args:
            queue_url: URL of the queue
            receipt_handle: Receipt handle from received message
            visibility_timeout: New timeout in seconds
        """
        try:
            self.client.change_message_visibility(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout,
            )

        except ClientError as e:
            logger.error(f"Failed to change message visibility: {e}")
            raise


# Singleton instance
_sqs_adapter: Optional[SQSAdapter] = None


def get_sqs_adapter() -> SQSAdapter:
    """Get or create SQS adapter singleton."""
    global _sqs_adapter
    if _sqs_adapter is None:
        _sqs_adapter = SQSAdapter()
    return _sqs_adapter
