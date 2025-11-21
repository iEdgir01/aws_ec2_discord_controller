"""Enhanced database module with metrics tracking and indexing

Provides async database operations for uptime tracking, cost monitoring,
and command auditing.
"""

import aiosqlite
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from pathlib import Path


class Database:
    """Async database manager for EC2 bot"""

    def __init__(self, db_path: str = "/data/ec2bot.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize database schema with indexes"""
        async with aiosqlite.connect(self.db_path) as db:
            # Uptime tracking table (enhanced)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS uptime (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    stop_time TEXT,
                    duration_seconds INTEGER,
                    created_at TEXT NOT NULL
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_uptime_date ON uptime(date)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_uptime_instance ON uptime(instance_id)")

            # Cost tracking table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    estimated_cost REAL NOT NULL,
                    instance_type TEXT,
                    region TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_costs_date ON costs(date)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_costs_instance ON costs(instance_id)")

            # Command audit log
            await db.execute("""
                CREATE TABLE IF NOT EXISTS command_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    command TEXT NOT NULL,
                    instance_id TEXT,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    executed_at TEXT NOT NULL
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_cmdlog_executed ON command_log(executed_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_cmdlog_user ON command_log(user_id)")

            # Instance metadata cache
            await db.execute("""
                CREATE TABLE IF NOT EXISTS instance_metadata (
                    instance_id TEXT PRIMARY KEY,
                    instance_type TEXT,
                    region TEXT,
                    launch_time TEXT,
                    tags TEXT,
                    last_updated TEXT NOT NULL
                )
            """)

            # Uptime alert configuration
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alert_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_name TEXT NOT NULL,
                    threshold_hours INTEGER NOT NULL,
                    reminder_interval_hours INTEGER DEFAULT 0,
                    enabled BOOLEAN DEFAULT 1,
                    channel_id TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Alert history/log
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id TEXT NOT NULL,
                    alert_config_id INTEGER NOT NULL,
                    alert_triggered_at TEXT NOT NULL,
                    uptime_hours REAL NOT NULL,
                    notification_sent BOOLEAN DEFAULT 0,
                    FOREIGN KEY (alert_config_id) REFERENCES alert_config (id)
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_alert_history_instance ON alert_history(instance_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_alert_history_triggered ON alert_history(alert_triggered_at)")

            await db.commit()

    async def start_uptime_session(self, instance_id: str) -> int:
        """Start a new uptime tracking session

        Args:
            instance_id: EC2 instance ID

        Returns:
            Session ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now(timezone.utc).isoformat()
            date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

            cursor = await db.execute("""
                INSERT INTO uptime (instance_id, date, start_time, created_at)
                VALUES (?, ?, ?, ?)
            """, (instance_id, date, now, now))

            await db.commit()
            return cursor.lastrowid

    async def end_uptime_session(self, instance_id: str) -> Optional[int]:
        """End the current uptime session

        Args:
            instance_id: EC2 instance ID

        Returns:
            Duration in seconds, or None if no active session
        """
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now(timezone.utc).isoformat()

            # Find most recent active session
            cursor = await db.execute("""
                SELECT id, start_time FROM uptime
                WHERE instance_id = ? AND stop_time IS NULL
                ORDER BY start_time DESC
                LIMIT 1
            """, (instance_id,))

            row = await cursor.fetchone()
            if not row:
                return None

            session_id, start_time = row
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            stop_dt = datetime.fromisoformat(now.replace('Z', '+00:00'))
            duration = int((stop_dt - start_dt).total_seconds())

            await db.execute("""
                UPDATE uptime
                SET stop_time = ?, duration_seconds = ?
                WHERE id = ?
            """, (now, duration, session_id))

            await db.commit()
            return duration

    async def get_daily_uptime(self, instance_id: str, date: Optional[str] = None) -> int:
        """Get total uptime for a specific day

        Args:
            instance_id: EC2 instance ID
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Total uptime in seconds
        """
        if not date:
            date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT SUM(duration_seconds) FROM uptime
                WHERE instance_id = ? AND date = ? AND duration_seconds IS NOT NULL
            """, (instance_id, date))

            row = await cursor.fetchone()
            return row[0] or 0

    async def get_monthly_uptime(self, instance_id: str, year: int, month: int) -> int:
        """Get total uptime for a specific month

        Args:
            instance_id: EC2 instance ID
            year: Year
            month: Month (1-12)

        Returns:
            Total uptime in seconds
        """
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT SUM(duration_seconds) FROM uptime
                WHERE instance_id = ? AND date >= ? AND date < ?
                AND duration_seconds IS NOT NULL
            """, (instance_id, start_date, end_date))

            row = await cursor.fetchone()
            return row[0] or 0

    async def log_command(self, user_id: str, username: str, command: str,
                         instance_id: Optional[str] = None, success: bool = True,
                         error_message: Optional[str] = None):
        """Log a command execution

        Args:
            user_id: Discord user ID
            username: Discord username
            command: Command executed
            instance_id: EC2 instance ID (if applicable)
            success: Whether command succeeded
            error_message: Error message if failed
        """
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now(timezone.utc).isoformat()
            await db.execute("""
                INSERT INTO command_log (user_id, username, command, instance_id,
                                        success, error_message, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, command, instance_id, success, error_message, now))
            await db.commit()

    async def save_instance_metadata(self, instance_id: str, instance_type: str,
                                     region: str, launch_time: str, tags: Dict[str, str]):
        """Cache instance metadata

        Args:
            instance_id: EC2 instance ID
            instance_type: Instance type (e.g., t2.micro)
            region: AWS region
            launch_time: Instance launch time
            tags: Instance tags
        """
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now(timezone.utc).isoformat()
            tags_json = json.dumps(tags)

            await db.execute("""
                INSERT OR REPLACE INTO instance_metadata
                (instance_id, instance_type, region, launch_time, tags, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (instance_id, instance_type, region, launch_time, tags_json, now))

            await db.commit()

    async def get_instance_metadata(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get cached instance metadata

        Args:
            instance_id: EC2 instance ID

        Returns:
            Instance metadata or None if not cached
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM instance_metadata WHERE instance_id = ?
            """, (instance_id,))

            row = await cursor.fetchone()
            if not row:
                return None

            return {
                "instance_id": row["instance_id"],
                "instance_type": row["instance_type"],
                "region": row["region"],
                "launch_time": row["launch_time"],
                "tags": json.loads(row["tags"]),
                "last_updated": row["last_updated"]
            }

    async def record_cost_estimate(self, instance_id: str, estimated_cost: float,
                                   instance_type: str, region: str):
        """Record estimated cost for a day

        Args:
            instance_id: EC2 instance ID
            estimated_cost: Estimated cost in USD
            instance_type: Instance type
            region: AWS region
        """
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now(timezone.utc)
            date = now.strftime('%Y-%m-%d')
            created_at = now.isoformat()

            await db.execute("""
                INSERT INTO costs (instance_id, date, estimated_cost,
                                  instance_type, region, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (instance_id, date, estimated_cost, instance_type, region, created_at))

            await db.commit()

    async def get_monthly_costs(self, year: int, month: int) -> List[Dict[str, Any]]:
        """Get all costs for a specific month

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            List of cost records
        """
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM costs
                WHERE date >= ? AND date < ?
                ORDER BY date DESC
            """, (start_date, end_date))

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def create_alert_config(self, alert_name: str, threshold_hours: int,
                                  reminder_interval_hours: int = 0, channel_id: Optional[str] = None) -> int:
        """Create a new uptime alert configuration

        Args:
            alert_name: Name of the alert (e.g., "4 Hour Warning")
            threshold_hours: Number of hours before alert triggers
            reminder_interval_hours: Hours between reminder alerts (0 = no reminders)
            channel_id: Discord channel ID for notifications (None = DM)

        Returns:
            Alert config ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now(timezone.utc).isoformat()

            cursor = await db.execute("""
                INSERT INTO alert_config (alert_name, threshold_hours, reminder_interval_hours,
                                         enabled, channel_id, created_at)
                VALUES (?, ?, ?, 1, ?, ?)
            """, (alert_name, threshold_hours, reminder_interval_hours, channel_id, now))

            await db.commit()
            return cursor.lastrowid

    async def get_alert_configs(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """Get all alert configurations

        Args:
            enabled_only: Only return enabled alerts

        Returns:
            List of alert configs
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if enabled_only:
                cursor = await db.execute("""
                    SELECT * FROM alert_config WHERE enabled = 1 ORDER BY threshold_hours ASC
                """)
            else:
                cursor = await db.execute("""
                    SELECT * FROM alert_config ORDER BY threshold_hours ASC
                """)

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_alert_config(self, alert_id: int, enabled: Optional[bool] = None,
                                  threshold_hours: Optional[int] = None,
                                  reminder_interval_hours: Optional[int] = None) -> bool:
        """Update an alert configuration

        Args:
            alert_id: Alert config ID
            enabled: Enable/disable the alert
            threshold_hours: New threshold
            reminder_interval_hours: New reminder interval

        Returns:
            True if updated, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            updates = []
            params = []

            if enabled is not None:
                updates.append("enabled = ?")
                params.append(enabled)

            if threshold_hours is not None:
                updates.append("threshold_hours = ?")
                params.append(threshold_hours)

            if reminder_interval_hours is not None:
                updates.append("reminder_interval_hours = ?")
                params.append(reminder_interval_hours)

            if not updates:
                return False

            params.append(alert_id)
            query = f"UPDATE alert_config SET {', '.join(updates)} WHERE id = ?"

            cursor = await db.execute(query, params)
            await db.commit()

            return cursor.rowcount > 0

    async def delete_alert_config(self, alert_id: int) -> bool:
        """Delete an alert configuration

        Args:
            alert_id: Alert config ID

        Returns:
            True if deleted, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM alert_config WHERE id = ?", (alert_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def log_alert(self, instance_id: str, alert_config_id: int, uptime_hours: float,
                       notification_sent: bool = False) -> int:
        """Log an alert trigger

        Args:
            instance_id: EC2 instance ID
            alert_config_id: Alert config ID that triggered
            uptime_hours: Current uptime in hours
            notification_sent: Whether notification was sent

        Returns:
            Alert history ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now(timezone.utc).isoformat()

            cursor = await db.execute("""
                INSERT INTO alert_history (instance_id, alert_config_id, alert_triggered_at,
                                          uptime_hours, notification_sent)
                VALUES (?, ?, ?, ?, ?)
            """, (instance_id, alert_config_id, now, uptime_hours, notification_sent))

            await db.commit()
            return cursor.lastrowid

    async def get_last_alert_for_instance(self, instance_id: str, alert_config_id: int) -> Optional[Dict[str, Any]]:
        """Get the last alert trigger for an instance and alert config

        Args:
            instance_id: EC2 instance ID
            alert_config_id: Alert config ID

        Returns:
            Last alert record or None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute("""
                SELECT * FROM alert_history
                WHERE instance_id = ? AND alert_config_id = ?
                ORDER BY alert_triggered_at DESC
                LIMIT 1
            """, (instance_id, alert_config_id))

            row = await cursor.fetchone()
            return dict(row) if row else None
