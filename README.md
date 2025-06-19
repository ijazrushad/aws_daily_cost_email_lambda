Of course. You are right, a wall of text is hard to read. A well-formatted and attractive `README` makes a project much more professional and easier to understand.

Let's create a much better version using modern GitHub Markdown styling, including badges, emojis, tables, and collapsible sections. This will look great on your GitHub repository.

-----

### **Copy the text below and paste it into your `README.md` file on GitHub.**

# 📊 AWS Daily Cost Reporting Email Lambda

A serverless project that automatically generates and sends a daily email summarizing your AWS account's costs. This report provides a clear, at-a-glance overview of your cloud spending, helping you stay on budget.

The function is written in Python, triggered on a daily schedule by Amazon EventBridge, and sends richly formatted HTML emails via Amazon SES.

## 🌟 Final Output

The generated email provides a clean, professional summary of your costs:

## ✨ Features

  - ✅ **Automated Daily Emails:** Receive a cost report in your inbox at a specific time every day.
  - ✅ **Key Cost Metrics:**
      - Month-to-Date Cost
      - Last 24h Cost
      - Forecasted Monthly Cost
  - ✅ **Detailed Breakdown:** A service-by-service list of costs, sorted from highest to lowest.
  - ✅ **Visual Cost Distribution:** A simple bar chart helps you instantly identify the highest-spending services.
  - ✅ **Serverless & Efficient:** Runs on AWS Lambda, so you only pay for the few seconds it runs each day.
  - ✅ **Easily Configurable:** Uses Lambda environment variables for easy changes without touching the code.

## 🔑 Prerequisites

Before you begin, ensure you have the following:

1.  An **AWS Account**.
2.  **IAM permissions** to create Roles, Policies, Lambda functions, and EventBridge rules.
3.  **Verified Email Addresses in Amazon SES.** Both the `sender` and `recipient` email addresses **must be verified** in the AWS Region you are deploying this function to (e.g., `ap-southeast-1`).

## 🚀 Setup and Deployment

Follow these steps to deploy the cost reporter in your AWS account.

### Step 1: Create IAM Policy & Role

The Lambda function needs specific permissions to run.

1.  **Create the IAM Policy:**

      - Navigate to the **IAM** service \> **Policies** \> **Create policy**.
      - Switch to the **JSON** tab and paste the contents of the [`IAM_Policy.json`](https://www.google.com/search?q=%23-iam-policy) provided below.
      - Name the policy `LambdaCostReporterPolicy`.

2.  **Create the IAM Role:**

      - Navigate to **IAM** \> **Roles** \> **Create role**.
      - **Trusted entity type:** `AWS service`.
      - **Use case:** `Lambda`.
      - Attach two policies:
          - `LambdaCostReporterPolicy` (the one you just created).
          - `AWSLambdaBasicExecutionRole` (an AWS managed policy).
      - Name the role `CostEmailRole`.

### Step 2: Create & Configure Lambda Function

1.  **Create Function:**

      - Navigate to the **Lambda** service \> **Create function**.
      - Select **Author from scratch**.
      - **Function name:** `DailyAWSCostReporter`
      - **Runtime:** `Python 3.12`
      - **Execution role:** Choose `Use an existing role` and select `CostEmailRole`.

2.  **Add Code:**

      - In the **Code source** editor, paste the entire Python script from the [`lambda_function.py`](https://www.google.com/search?q=%23-lambda-function) section below.
      - Click the **Deploy** button.

3.  **Add Configuration:**

      - Go to the **Configuration** tab.
      - In **General configuration**, set the **Timeout** to `30 seconds`.
      - In **Environment variables**, add the following key-value pairs:

| Key               | Value                           |
| ----------------- | ------------------------------- |
| `SENDER_EMAIL`    | `your-verified-sender@email.com`  |
| `RECIPIENT_EMAIL` | `your-recipient@email.com`        |

### Step 3: Create the EventBridge Trigger

1.  From your Lambda function's page, click **+ Add trigger**.
2.  **Source:** Select **EventBridge (CloudWatch Events)**.
3.  **Rule:** Choose **Create a new rule**.
4.  **Rule name:** `RunDailyCostReporter`.
5.  **Schedule expression:** To run at a specific time daily, use a cron expression. **Note: EventBridge uses UTC time.**
      - *Example:* To run at 9:00 AM in Dhaka (UTC+6), you must set the schedule for 3:00 AM UTC. The expression is:
        ```
        cron(0 3 * * ? *)
        ```

-----

## 💻 Code & Policies

\<details\>
\<summary\>\<strong\>Click to view the Python code for \<code\>lambda\_function.py\</code\>\</strong\>\</summary\>

```python
import boto3
import datetime
import os

# Initialize AWS clients outside the handler for better performance
ce = boto3.client('ce', region_name='ap-southeast-1')
ses = boto3.client('ses', region_name='ap-southeast-1')

def lambda_handler(event, context):
    """
    Main function to fetch AWS cost data, format it, and send it via email.
    """
    try:
        # --- 1. CONFIGURATION ---
        # Get configuration from Lambda Environment Variables for security and flexibility
        sender_email = os.environ.get('SENDER_EMAIL')
        recipient_email = os.environ.get('RECIPIENT_EMAIL')
        aws_account_id = context.invoked_function_arn.split(":")[4]

        # --- 2. DATE CALCULATIONS ---
        today = datetime.datetime.now()
        yesterday = today - datetime.timedelta(days=1)
        
        start_of_month = today.strftime('%Y-%m-01')
        end_of_period = today.strftime('%Y-%m-%d')
        yesterday_str = yesterday.strftime('%Y-%m-%d')

        future_date = today + datetime.timedelta(days=30)
        forecast_end_date = future_date.strftime('%Y-%m-%d')

        # --- 3. AWS API CALLS ---
        # Get Month-to-Date cost breakdown by service
        service_breakdown_response = ce.get_cost_and_usage(
            TimePeriod={'Start': start_of_month, 'End': end_of_period},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )

        # Get the monthly cost forecast
        forecast_response = ce.get_cost_forecast(
            TimePeriod={'Start': end_of_period, 'End': forecast_end_date},
            Metric='UNBLENDED_COST',
            Granularity='MONTHLY'
        )
        forecasted_cost = float(forecast_response['Total']['Amount'])

        # Get cost from the last 24 hours
        daily_cost_response = ce.get_cost_and_usage(
            TimePeriod={'Start': yesterday_str, 'End': end_of_period},
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )
        # Handle cases where there might be no cost data yet (e.g., new day)
        daily_cost = float(daily_cost_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']) if daily_cost_response['ResultsByTime'] else 0.0

        # --- 4. PROCESS DATA ---
        service_costs = {}
        total_cost = 0.0
        
        for result in service_breakdown_response['ResultsByTime'][0]['Groups']:
            service_name = result['Keys'][0]
            cost_amount = float(result['Metrics']['UnblendedCost']['Amount'])
            if cost_amount > 0.0:  # Filter out zero-cost services
                service_costs[service_name] = cost_amount
                total_cost += cost_amount

        # Sort services by cost to find top spenders
        sorted_services = sorted(service_costs.items(), key=lambda item: item[1], reverse=True)
        # Use the highest cost for scaling the bar chart, avoid division by zero
        max_cost = sorted_services[0][1] if sorted_services else 1.0

        # --- 5. BUILD AND SEND EMAIL ---
        subject = f"AWS Cost Summary for {aws_account_id} - {today.strftime('%Y-%m-%d')}"
        body = build_html_body(total_cost, forecasted_cost, daily_cost, sorted_services, max_cost)
        
        send_email(sender_email, recipient_email, subject, body)
        
        return {'statusCode': 200, 'body': 'Email sent successfully!'}

    except Exception as e:
        print(f"An error occurred in the handler: {str(e)}")
        return {'statusCode': 500, 'body': f'An error occurred: {str(e)}'}


def build_html_body(total, forecast, daily, services, max_cost):
    """
    Builds the HTML content for the email report.
    """
    html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; margin: 0; padding: 0; background-color: #f7f7f7;}}
        .container {{ max-width: 800px; margin: 20px auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ font-size: 24px; color: #d9534f; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; margin-bottom: 20px; }}
        .summary-box {{ display: flex; justify-content: space-around; background-color: #f9f9f9; padding: 20px; text-align: center; border-radius: 8px; margin-bottom: 30px; }}
        .summary-item h3 {{ margin: 0; font-size: 16px; color: #555; font-weight: normal; }}
        .summary-item p {{ margin: 5px 0 0; font-size: 28px; font-weight: bold; color: #0275d8; }}
        h2 {{ font-size: 20px; color: #333; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px;}}
        th, td {{ padding: 12px; border: 1px solid #ddd; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .bar-container {{ width: 100%; background-color: #f1f1f1; border-radius: 4px; height: 22px; }}
        .bar {{ height: 22px; background-color: #4CAF50; border-radius: 4px; text-align: right; color: white; line-height: 22px; }}
    </style>
    </head>
    <body>
    <div class="container">
        <div class="header">AWS Cost Report</div>
        <div class="summary-box">
            <div class="summary-item">
                <h3>Month-to-Date Cost</h3>
                <p>${total:,.2f}</p>
            </div>
            <div class="summary-item">
                <h3>Last 24h Cost</h3>
                <p>${daily:,.2f}</p>
            </div>
            <div class="summary-item">
                <h3>Forecasted Monthly Cost</h3>
                <p>${forecast:,.2f}</p>
            </div>
        </div>
        
        <h2>Service-wise Cost Breakdown</h2>
        <table>
            <tr>
                <th style="width:40%;">Service</th>
                <th style="width:20%;">Cost (USD)</th>
                <th>Cost Distribution</th>
            </tr>
    """
    
    for service, cost in services:
        bar_width = (cost / max_cost) * 100 if max_cost > 0 else 0
        html += f"""
            <tr>
                <td>{service}</td>
                <td style="text-align: right;">${cost:,.2f}</td>
                <td>
                    <div class="bar-container">
                        <div class="bar" style="width: {bar_width:.2f}%; background-color: #5cb85c;"></div>
                    </div>
                </td>
            </tr>
        """
        
    html += """
        </table>
    </div>
    </body>
    </html>
    """
    return html

def send_email(source, to, subject, body):
    """
    Sends an email using AWS SES.
    """
    try:
        response = ses.send_email(
            Source=source,
            Destination={'ToAddresses': [to]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': body, 'Charset': 'UTF-8'}}
            }
        )
        print(f"Email sent successfully. Message ID: {response['MessageId']}")
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        # Re-raise the exception to make the Lambda handler fail if email sending fails
        raise e
```

\</details\>

\<details\>
\<summary\>\<strong\>Click to view the JSON for \<code\>IAM\_Policy.json\</code\>\</strong\>\</summary\>

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ses:SendEmail"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetCostForecast"
            ],
            "Resource": "*"
        }
    ]
}
```

\</details\>

## 🤔 Troubleshooting

| Error                                                                    | Cause                                                         | Solution                                                                                                   |
| ------------------------------------------------------------------------ | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `AccessDeniedException` when calling `GetCostForecast`                     | The IAM role is missing the `ce:GetCostForecast` permission.    | Add the permission to your IAM policy as shown in the `IAM_Policy.json` file.                              |
| `Parameter validation failed: ... value: None` for `Source` or `Destination` | Environment variables are not set in the Lambda configuration.  | Go to Lambda \> Configuration \> Environment variables and add `SENDER_EMAIL` and `RECIPIENT_EMAIL`.         |
| Email not received, but logs say "success"                               | The sender's email address is not verified in Amazon SES.       | Go to the Amazon SES console and verify the sender's email identity.                                       |

## 📄 License

MIT License

Copyright (c) 2025 [Your Name or GitHub Username]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.