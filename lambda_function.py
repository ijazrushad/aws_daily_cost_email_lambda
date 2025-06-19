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
        sender_email = os.environ.get('SENDER_EMAIL', 'itsupport@adplay-mobile.com')
        recipient_email = os.environ.get('RECIPIENT_EMAIL', 'itsupport@vumobile.biz')
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
        # Optionally send an error email
        # send_email(sender_email, recipient_email, "Error in Cost Report Lambda", f"An error occurred: {str(e)}")
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