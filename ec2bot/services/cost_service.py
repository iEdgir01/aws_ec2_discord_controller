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

    async def get_cost_breakdown_by_service(self, year: int, month: int) -> Dict[str, Any]:
        """Get cost breakdown by AWS service for EC2-related services

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Dict with cost breakdown by service
        """
        start_date = f"{year}-{month:02d}-01"

        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        try:
            async def fetch_breakdown():
                response = self.ce_client.get_cost_and_usage(
                    TimePeriod={
                        'Start': start_date,
                        'End': end_date
                    },
                    Granularity='MONTHLY',
                    Metrics=['UnblendedCost'],
                    GroupBy=[
                        {
                            'Type': 'DIMENSION',
                            'Key': 'SERVICE'
                        }
                    ],
                    Filter={
                        'Or': [
                            {
                                'Dimensions': {
                                    'Key': 'SERVICE',
                                    'Values': ['Amazon Elastic Compute Cloud - Compute']
                                }
                            },
                            {
                                'Dimensions': {
                                    'Key': 'SERVICE',
                                    'Values': ['EC2 - Other']
                                }
                            },
                            {
                                'Dimensions': {
                                    'Key': 'USAGE_TYPE_GROUP',
                                    'Values': ['EC2: EBS - Storage']
                                }
                            }
                        ]
                    }
                )
                return response

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, fetch_breakdown)

            breakdown = {}
            total_cost = 0.0

            if response['ResultsByTime']:
                for group in response['ResultsByTime'][0]['Groups']:
                    service = group['Keys'][0]
                    amount = float(group['Metrics']['UnblendedCost']['Amount'])

                    # Map AWS service names to friendly names
                    service_name = self._map_service_name(service)
                    breakdown[service_name] = amount
                    total_cost += amount

            return {
                "year": year,
                "month": month,
                "breakdown": breakdown,
                "total_cost": total_cost,
                "currency": "USD",
                "source": "AWS Cost Explorer"
            }

        except Exception as e:
            return {
                "year": year,
                "month": month,
                "breakdown": {},
                "total_cost": 0.0,
                "currency": "USD",
                "source": "Unavailable",
                "error": str(e)
            }

    def _map_service_name(self, aws_service_name: str) -> str:
        """Map AWS service names to user-friendly names

        Args:
            aws_service_name: AWS service name

        Returns:
            User-friendly service name
        """
        mapping = {
            "Amazon Elastic Compute Cloud - Compute": "EC2 Instances",
            "EC2 - Other": "Elastic IP & Data Transfer",
            "Amazon Elastic Block Store": "EBS Storage (gp3)",
        }
        return mapping.get(aws_service_name, aws_service_name)

    async def get_cost_optimization_recommendations(self, year: int, month: int) -> List[Dict[str, str]]:
        """Generate cost optimization recommendations based on usage

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            List of recommendation dicts with 'severity', 'title', and 'message'
        """
        recommendations = []

        try:
            # Get cost breakdown
            breakdown_data = await self.get_cost_breakdown_by_service(year, month)
            breakdown = breakdown_data.get('breakdown', {})
            total_cost = breakdown_data.get('total_cost', 0.0)

            # Get daily costs for trend analysis
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year + 1}-01-01"
            else:
                end_date = f"{year}-{month + 1:02d}-01"

            daily_costs = await self.get_daily_costs(start_date, end_date)

            # Recommendation 1: High Elastic IP costs
            eip_cost = breakdown.get("Elastic IP & Data Transfer", 0.0)
            if eip_cost > 5.0:  # $5/month threshold
                recommendations.append({
                    "severity": "medium",
                    "title": "High Elastic IP Costs",
                    "message": f"You're spending ${eip_cost:.2f}/month on Elastic IPs. "
                              f"Consider releasing unused Elastic IPs or using dynamic IPs for development instances."
                })

            # Recommendation 2: Instance running costs
            instance_cost = breakdown.get("EC2 Instances", 0.0)
            if instance_cost > 20.0:  # $20/month threshold
                recommendations.append({
                    "severity": "high",
                    "title": "Consider Reserved Instances",
                    "message": f"You're spending ${instance_cost:.2f}/month on EC2 compute. "
                              f"If you run instances consistently, Reserved Instances could save up to 70%."
                })

            # Recommendation 3: Storage costs
            storage_cost = breakdown.get("EBS Storage (gp3)", 0.0)
            if storage_cost > 10.0:
                recommendations.append({
                    "severity": "low",
                    "title": "Storage Optimization",
                    "message": f"You're spending ${storage_cost:.2f}/month on EBS storage. "
                              f"Review and delete unused snapshots or volumes to reduce costs."
                })

            # Recommendation 4: Daily cost spikes
            if len(daily_costs) > 1:
                avg_cost = sum(d['cost'] for d in daily_costs) / len(daily_costs)
                max_cost = max(d['cost'] for d in daily_costs)

                if max_cost > avg_cost * 2:  # More than 2x average
                    recommendations.append({
                        "severity": "medium",
                        "title": "Cost Spike Detected",
                        "message": f"Daily costs show spikes up to ${max_cost:.2f} (average: ${avg_cost:.2f}). "
                                  f"Review instance uptime patterns and consider stopping instances when not in use."
                    })

            # Recommendation 5: Overall cost warning
            if total_cost > 50.0:
                recommendations.append({
                    "severity": "high",
                    "title": "High Monthly Costs",
                    "message": f"Total monthly cost is ${total_cost:.2f}. "
                              f"Enable AWS Budget alerts and review your instance usage patterns."
                })

            # Recommendation 6: Low utilization (no costs)
            if total_cost < 1.0 and len(daily_costs) > 0:
                recommendations.append({
                    "severity": "info",
                    "title": "Excellent Cost Management",
                    "message": f"Your monthly cost is only ${total_cost:.2f}. "
                              f"Great job managing your instance uptime!"
                })

            return recommendations

        except Exception as e:
            return [{
                "severity": "error",
                "title": "Unable to Generate Recommendations",
                "message": f"Error analyzing costs: {str(e)}"
            }]
