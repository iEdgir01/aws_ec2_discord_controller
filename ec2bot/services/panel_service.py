"""Pterodactyl Panel service with async support

Provides panel operations with error handling and async support.
"""

import asyncio
from typing import Dict, List, Optional, Any
from api import serverData, serverState, generateResourcesURL, list_running_servers as list_running
from functions import get_server_statuses, server_details, dataframe


class PanelServiceError(Exception):
    """Base exception for Panel service errors"""
    pass


class PanelService:
    """Pterodactyl Panel service with async support"""

    def __init__(self):
        """Initialize Panel service"""
        pass

    async def _run_in_executor(self, func, *args):
        """Run synchronous function in executor to avoid blocking

        Args:
            func: Function to execute
            *args: Arguments for the function

        Returns:
            Function result

        Raises:
            PanelServiceError: If execution fails
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: func(*args))
            return result
        except Exception as e:
            raise PanelServiceError(f"Panel API error: {str(e)}")

    async def get_server_list(self) -> Dict[str, Dict[str, str]]:
        """Get list of all servers

        Returns:
            Dict of server data with name as key
        """
        try:
            server_data = await self._run_in_executor(serverData)
            if not server_data:
                return {}
            return server_data
        except Exception as e:
            raise PanelServiceError(f"Failed to get server list: {str(e)}")

    async def get_server_states(self) -> Dict[str, Any]:
        """Get current state of all servers

        Returns:
            Dict with server names and their states
        """
        try:
            urls = await self._run_in_executor(generateResourcesURL)
            if not urls:
                return {}

            states = await self._run_in_executor(serverState, urls)
            if isinstance(states, str) and "Error" in states:
                raise PanelServiceError(states)

            return states
        except Exception as e:
            raise PanelServiceError(f"Failed to get server states: {str(e)}")

    async def get_running_servers(self) -> List[str]:
        """Get list of running server names

        Returns:
            List of running server names
        """
        try:
            states = await self.get_server_states()
            running = []
            for name, data in states.items():
                if data.get('state') == 'running':
                    running.append(name)
            return running
        except Exception as e:
            raise PanelServiceError(f"Failed to get running servers: {str(e)}")

    async def get_server_details_table(self) -> str:
        """Get formatted table of server details

        Returns:
            Markdown formatted table string
        """
        try:
            states = await self.get_server_states()
            if not states:
                return "No servers found"

            # Check if any servers are running
            has_running = any(data.get('state') == 'running' for data in states.values())
            if not has_running:
                return "No servers are currently running"

            df = await self._run_in_executor(dataframe, states)
            table = await self._run_in_executor(server_details, df)
            return table
        except Exception as e:
            raise PanelServiceError(f"Failed to get server details: {str(e)}")

    async def get_server_count(self) -> Dict[str, int]:
        """Get count of servers by state

        Returns:
            Dict with counts: {'total', 'running', 'offline', 'starting', 'stopping'}
        """
        try:
            states = await self.get_server_states()

            counts = {
                'total': len(states),
                'running': 0,
                'offline': 0,
                'starting': 0,
                'stopping': 0
            }

            for data in states.values():
                state = data.get('state', 'unknown').lower()
                if state in counts:
                    counts[state] += 1
                else:
                    counts['offline'] += 1

            return counts
        except Exception as e:
            raise PanelServiceError(f"Failed to get server count: {str(e)}")
