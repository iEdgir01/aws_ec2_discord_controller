"""EC2 service with caching and error handling

Provides EC2 operations with retry logic, caching, and comprehensive error handling.
"""

import boto3
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, BotoCoreError
import time

from .cache_service import get_cache


class EC2ServiceError(Exception):
    """Base exception for EC2 service errors"""
    pass


class EC2Service:
    """AWS EC2 service with caching and retry logic"""

    def __init__(self, region: str = "us-east-1"):
        """Initialize EC2 service

        Args:
            region: AWS region
        """
        self.region = region
        self.ec2_resource = boto3.resource('ec2', region_name=region)
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.cache = get_cache()

    async def _retry_with_backoff(self, func, *args, max_retries: int = 3, **kwargs):
        """Execute function with exponential backoff retry

        Args:
            func: Function to execute
            max_retries: Maximum number of retries
            *args, **kwargs: Arguments for the function

        Returns:
            Function result

        Raises:
            EC2ServiceError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
                return result

            except (ClientError, BotoCoreError) as e:
                if attempt == max_retries - 1:
                    raise EC2ServiceError(f"AWS API error after {max_retries} attempts: {str(e)}")

                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)

            except Exception as e:
                raise EC2ServiceError(f"Unexpected error: {str(e)}")

    async def get_instances_by_tag(self, tag_key: str, tag_value: str, use_cache: bool = True) -> List[Any]:
        """Get EC2 instances filtered by tag

        Args:
            tag_key: Tag key to filter by
            tag_value: Tag value to filter by
            use_cache: Whether to use cache

        Returns:
            List of EC2 instance objects
        """
        cache_key = f"instances:{tag_key}:{tag_value}"

        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        def fetch_instances():
            filters = [{'Name': f'tag:{tag_key}', 'Values': [tag_value]}]
            instances = list(self.ec2_resource.instances.filter(Filters=filters))
            return instances

        instances = await self._retry_with_backoff(fetch_instances)

        if use_cache:
            await self.cache.set(cache_key, instances, ttl_seconds=30)

        return instances

    async def get_instance_state(self, instance_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get instance state with caching

        Args:
            instance_id: EC2 instance ID
            use_cache: Whether to use cache

        Returns:
            Dict with instance state information
        """
        cache_key = f"state:{instance_id}"

        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        def fetch_state():
            instance = self.ec2_resource.Instance(instance_id)
            instance.load()  # Refresh state

            state_info = {
                "instance_id": instance_id,
                "state": instance.state['Name'],
                "state_code": instance.state['Code'],
                "instance_type": instance.instance_type,
                "public_ip": instance.public_ip_address,
                "private_ip": instance.private_ip_address,
                "launch_time": instance.launch_time.isoformat() if instance.launch_time else None,
                "availability_zone": instance.placement['AvailabilityZone'],
                "tags": {tag['Key']: tag['Value'] for tag in (instance.tags or [])}
            }

            return state_info

        state = await self._retry_with_backoff(fetch_state)

        if use_cache:
            await self.cache.set(cache_key, state, ttl_seconds=30)

        return state

    async def start_instance(self, instance_id: str) -> Dict[str, Any]:
        """Start an EC2 instance

        Args:
            instance_id: EC2 instance ID

        Returns:
            Dict with operation result
        """
        start_time = time.time()

        try:
            def do_start():
                instance = self.ec2_resource.Instance(instance_id)
                response = instance.start()
                return response

            response = await self._retry_with_backoff(do_start)

            # Invalidate cache
            await self.cache.delete(f"state:{instance_id}")

            duration_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "instance_id": instance_id,
                "previous_state": response['StartingInstances'][0]['PreviousState']['Name'],
                "current_state": response['StartingInstances'][0]['CurrentState']['Name'],
                "duration_ms": duration_ms
            }

        except EC2ServiceError as e:
            return {
                "success": False,
                "instance_id": instance_id,
                "error": str(e),
                "duration_ms": (time.time() - start_time) * 1000
            }

    async def stop_instance(self, instance_id: str) -> Dict[str, Any]:
        """Stop an EC2 instance

        Args:
            instance_id: EC2 instance ID

        Returns:
            Dict with operation result
        """
        start_time = time.time()

        try:
            def do_stop():
                instance = self.ec2_resource.Instance(instance_id)
                response = instance.stop()
                return response

            response = await self._retry_with_backoff(do_stop)

            # Invalidate cache
            await self.cache.delete(f"state:{instance_id}")

            duration_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "instance_id": instance_id,
                "previous_state": response['StoppingInstances'][0]['PreviousState']['Name'],
                "current_state": response['StoppingInstances'][0]['CurrentState']['Name'],
                "duration_ms": duration_ms
            }

        except EC2ServiceError as e:
            return {
                "success": False,
                "instance_id": instance_id,
                "error": str(e),
                "duration_ms": (time.time() - start_time) * 1000
            }

    async def reboot_instance(self, instance_id: str) -> Dict[str, Any]:
        """Reboot an EC2 instance

        Args:
            instance_id: EC2 instance ID

        Returns:
            Dict with operation result
        """
        start_time = time.time()

        try:
            def do_reboot():
                instance = self.ec2_resource.Instance(instance_id)
                instance.reboot()
                return True

            await self._retry_with_backoff(do_reboot)

            # Invalidate cache
            await self.cache.delete(f"state:{instance_id}")

            duration_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "instance_id": instance_id,
                "duration_ms": duration_ms
            }

        except EC2ServiceError as e:
            return {
                "success": False,
                "instance_id": instance_id,
                "error": str(e),
                "duration_ms": (time.time() - start_time) * 1000
            }

    async def get_instance_uptime(self, instance_id: str) -> Optional[timedelta]:
        """Calculate instance uptime

        Args:
            instance_id: EC2 instance ID

        Returns:
            Uptime as timedelta, or None if not running
        """
        state = await self.get_instance_state(instance_id)

        if state['state'] != 'running' or not state['launch_time']:
            return None

        launch_time = datetime.fromisoformat(state['launch_time'].replace('Z', '+00:00'))
        now = datetime.now(launch_time.tzinfo)

        return now - launch_time

    async def wait_for_state(self, instance_id: str, desired_state: str,
                            timeout_seconds: int = 300, poll_interval: int = 5) -> bool:
        """Wait for instance to reach desired state

        Args:
            instance_id: EC2 instance ID
            desired_state: Desired state (e.g., 'running', 'stopped')
            timeout_seconds: Maximum time to wait
            poll_interval: Seconds between polls

        Returns:
            True if state reached, False if timeout
        """
        start_time = time.time()

        while (time.time() - start_time) < timeout_seconds:
            state = await self.get_instance_state(instance_id, use_cache=False)

            if state['state'] == desired_state:
                return True

            await asyncio.sleep(poll_interval)

        return False
