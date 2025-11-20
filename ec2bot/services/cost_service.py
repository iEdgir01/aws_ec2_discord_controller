"""AWS Cost Explorer integration for cost tracking

Provides cost estimation and tracking using AWS Cost Explorer API.
"""

import boto3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal


# EC2 pricing per hour (approximate, varies by region - use for estimates)
EC2_PRICING = {
    "t2.micro": 0.0116,
    "t2.small": 0.023,
    "t2.medium": 0.0464,
    "t3.micro": 0.0104,
    "t3.small": 0.0208,
    "t3.medium": 0.0416,
    "t3a.micro": 0.0094,
    "t3a.small": 0.0188,
    "t3a.medium": 0.0376,
    "t4g.micro": 0.0084,
    "t4g.small": 0.0168,
    "t4g.medium": 0.0336,
}


class CostService:
    """AWS Cost tracking and estimation"""

    def __init__(self, region: str = "us-east-1"):
        """Initialize Cost service

        Args:
            region: AWS region
        """
        self.region = region
        # Cost Explorer is only available in us-east-1
        self.ce_client = boto3.client('ce', region_name='us-east-1')

    async def get_monthly_costs(self, year: int, month: int) -> Dict[str, Any]:
        """Get actual costs from AWS Cost Explorer for a month

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Dict with cost information
        """
        start_date = f"{year}-{month:02d}-01"

        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        try:
            async def fetch_costs():
                response = self.ce_client.get_cost_and_usage(
                    TimePeriod={
                        'Start': start_date,
                        'End': end_date
                    },
                    Granularity='MONTHLY',
                    Metrics=['UnblendedCost'],
                    Filter={
                        'Dimensions': {
                            'Key': 'SERVICE',
                            'Values': ['Amazon Elastic Compute Cloud - Compute']
                        }
                    }
                )
                return response

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, fetch_costs)

            total_cost = 0.0
            if response['ResultsByTime']:
                amount = response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
                total_cost = float(amount)

            return {
                "year": year,
                "month": month,
                "total_cost": total_cost,
                "currency": "USD",
                "service": "EC2",
                "source": "AWS Cost Explorer"
            }

        except Exception as e:
            # Fall back to estimation if Cost Explorer unavailable
            return {
                "year": year,
                "month": month,
                "total_cost": 0.0,
                "currency": "USD",
                "service": "EC2",
                "source": "Unavailable",
                "error": str(e)
            }

    async def estimate_instance_cost(self, instance_type: str, uptime_hours: float) -> float:
        """Estimate cost for an instance based on uptime

        Args:
            instance_type: EC2 instance type
            uptime_hours: Hours the instance was running

        Returns:
            Estimated cost in USD
        """
        hourly_rate = EC2_PRICING.get(instance_type, 0.0)
        return hourly_rate * uptime_hours

    async def estimate_monthly_cost(self, instance_type: str, uptime_seconds: int) -> float:
        """Estimate monthly cost for an instance

        Args:
            instance_type: EC2 instance type
            uptime_seconds: Total uptime in seconds

        Returns:
            Estimated monthly cost in USD
        """
        uptime_hours = uptime_seconds / 3600.0
        return await self.estimate_instance_cost(instance_type, uptime_hours)

    async def get_cost_forecast(self, days: int = 30) -> Dict[str, Any]:
        """Get cost forecast for the next N days

        Args:
            days: Number of days to forecast

        Returns:
            Dict with forecast information
        """
        start_date = datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')

        try:
            async def fetch_forecast():
                response = self.ce_client.get_cost_forecast(
                    TimePeriod={
                        'Start': start_date,
                        'End': end_date
                    },
                    Metric='UNBLENDED_COST',
                    Granularity='MONTHLY',
                    Filter={
                        'Dimensions': {
                            'Key': 'SERVICE',
                            'Values': ['Amazon Elastic Compute Cloud - Compute']
                        }
                    }
                )
                return response

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, fetch_forecast)

            forecast_cost = float(response['Total']['Amount'])

            return {
                "forecast_days": days,
                "forecasted_cost": forecast_cost,
                "currency": "USD",
                "service": "EC2"
            }

        except Exception as e:
            return {
                "forecast_days": days,
                "forecasted_cost": 0.0,
                "currency": "USD",
                "service": "EC2",
                "error": str(e)
            }

    async def get_daily_costs(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get daily cost breakdown

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of daily cost records
        """
        try:
            async def fetch_daily():
                response = self.ce_client.get_cost_and_usage(
                    TimePeriod={
                        'Start': start_date,
                        'End': end_date
                    },
                    Granularity='DAILY',
                    Metrics=['UnblendedCost'],
                    Filter={
                        'Dimensions': {
                            'Key': 'SERVICE',
                            'Values': ['Amazon Elastic Compute Cloud - Compute']
                        }
                    }
                )
                return response

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, fetch_daily)

            daily_costs = []
            for result in response['ResultsByTime']:
                daily_costs.append({
                    "date": result['TimePeriod']['Start'],
                    "cost": float(result['Total']['UnblendedCost']['Amount']),
                    "currency": "USD"
                })

            return daily_costs

        except Exception as e:
            return []

    def format_cost_summary(self, cost: float, currency: str = "USD") -> str:
        """Format cost for display

        Args:
            cost: Cost amount
            currency: Currency code

        Returns:
            Formatted cost string
        """
        if currency == "USD":
            return f"${cost:.2f}"
        return f"{cost:.2f} {currency}"
