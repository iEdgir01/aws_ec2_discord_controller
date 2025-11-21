# AWS IAM Cost Tracking Setup Guide

This guide will help you set up IAM policies for cost tracking in your EC2 Discord Bot.

## Overview

To properly manage your EC2 instance and track costs, you'll need two separate IAM policies:

1. **EC2 Instance Management Policy** - For starting/stopping instances
2. **Cost Explorer Read-Only Policy** - For viewing and tracking costs

## Current Setup

Your existing IAM user has the following EC2 management policy:

```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"ec2:StartInstances",
				"ec2:RunInstances",
				"ec2:StopInstances"
			],
			"Resource": "arn:aws:ec2:*:962355420841:instance/i-0602f49e9ad9a3aea"
		},
		{
			"Sid": "VisualEditor1",
			"Effect": "Allow",
			"Action": [
				"ec2:DescribeInstances",
				"ec2:DescribeInstanceStatus"
			],
			"Resource": "*"
		}
	]
}
```

## Step 1: Create Cost Explorer Policy

### Policy JSON

Create a new policy with the following JSON:

```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "CostExplorerReadAccess",
			"Effect": "Allow",
			"Action": [
				"ce:GetCostAndUsage",
				"ce:GetCostForecast",
				"ce:GetDimensionValues",
				"ce:GetTags",
				"ce:GetCostCategories"
			],
			"Resource": "*"
		},
		{
			"Sid": "ViewBillingDashboard",
			"Effect": "Allow",
			"Action": [
				"aws-portal:ViewBilling",
				"aws-portal:ViewUsage"
			],
			"Resource": "*"
		},
		{
			"Sid": "EC2PricingAccess",
			"Effect": "Allow",
			"Action": [
				"pricing:GetProducts"
			],
			"Resource": "*"
		}
	]
}
```

### Creating the Policy via AWS Console

1. Sign in to the [AWS IAM Console](https://console.aws.amazon.com/iam/)

2. In the left navigation pane, click **Policies**

3. Click **Create policy**

4. Click the **JSON** tab

5. Paste the Cost Explorer policy JSON above

6. Click **Next: Tags** (optionally add tags)

7. Click **Next: Review**

8. Enter policy details:
   - **Name**: `EC2Bot-CostExplorer-ReadOnly`
   - **Description**: `Allows the EC2 Discord Bot to read cost and usage data from AWS Cost Explorer`

9. Click **Create policy**

### Creating the Policy via AWS CLI

```bash
# Create the policy JSON file
cat > ec2bot-cost-policy.json << 'EOF'
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "CostExplorerReadAccess",
			"Effect": "Allow",
			"Action": [
				"ce:GetCostAndUsage",
				"ce:GetCostForecast",
				"ce:GetDimensionValues",
				"ce:GetTags",
				"ce:GetCostCategories"
			],
			"Resource": "*"
		},
		{
			"Sid": "ViewBillingDashboard",
			"Effect": "Allow",
			"Action": [
				"aws-portal:ViewBilling",
				"aws-portal:ViewUsage"
			],
			"Resource": "*"
		},
		{
			"Sid": "EC2PricingAccess",
			"Effect": "Allow",
			"Action": [
				"pricing:GetProducts"
			],
			"Resource": "*"
		}
	]
}
EOF

# Create the policy
aws iam create-policy \
    --policy-name EC2Bot-CostExplorer-ReadOnly \
    --policy-document file://ec2bot-cost-policy.json \
    --description "Allows the EC2 Discord Bot to read cost and usage data from AWS Cost Explorer"
```

## Step 2: Attach Policies to IAM User

You need to attach both policies to your IAM user.

### Via AWS Console

1. Go to [IAM Users](https://console.aws.amazon.com/iam/home#/users)

2. Click on your IAM user (the one using the access key in your `.env` file)

3. Click the **Permissions** tab

4. Click **Add permissions** → **Attach existing policies directly**

5. Search for and select:
   - Your existing EC2 instance management policy
   - `EC2Bot-CostExplorer-ReadOnly` (the policy you just created)

6. Click **Next: Review** → **Add permissions**

### Via AWS CLI

```bash
# Get your IAM username
IAM_USER="your-iam-username"

# Attach the cost policy
aws iam attach-user-policy \
    --user-name $IAM_USER \
    --policy-arn "arn:aws:iam::962355420841:policy/EC2Bot-CostExplorer-ReadOnly"

# Verify attached policies
aws iam list-attached-user-policies --user-name $IAM_USER
```

## Step 3: Enable Cost Explorer (If Not Already Enabled)

Cost Explorer must be enabled in your AWS account:

1. Sign in to the [AWS Billing and Cost Management Console](https://console.aws.amazon.com/billing/)

2. In the navigation pane, click **Cost Explorer**

3. If prompted, click **Enable Cost Explorer**

4. Wait a few hours for AWS to process your cost data (initial setup can take up to 24 hours)

## Step 4: Test the Setup

Run the Discord bot and use the `.menu` command, then click **View Costs** to test if cost data is being retrieved properly.

### Troubleshooting

If you get permission errors:

1. **Check IAM Policy Attachment**:
   ```bash
   aws iam list-attached-user-policies --user-name your-iam-username
   ```

2. **Verify Cost Explorer is Enabled**:
   - Go to AWS Billing Console → Cost Explorer
   - Ensure it shows cost data

3. **Wait for Data Propagation**:
   - Cost Explorer data can take up to 24 hours to become available for new accounts

4. **Check CloudWatch Logs**:
   - The bot logs will show specific AWS API errors

## Cost Breakdown Features

Once set up, your bot will be able to:

- ✅ View current month EC2 costs
- ✅ Get 30-day cost forecasts
- ✅ Break down costs by service:
  - EC2 compute instances
  - Elastic IP addresses
  - EBS volumes (gp3 storage)
- ✅ Receive cost optimization recommendations
- ✅ Track daily and monthly cost trends

## Security Best Practices

1. **Principle of Least Privilege**: The cost policy only grants read access to billing data

2. **No Write Access**: The bot cannot modify billing settings or create resources

3. **Service-Specific**: Policies are scoped to specific services (EC2, Cost Explorer)

4. **Regular Audits**: Review IAM permissions quarterly to ensure they're still needed

## Additional Resources

- [AWS Cost Explorer Documentation](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html)
- [AWS IAM Policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html)
- [AWS Pricing API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/price-changes.html)
