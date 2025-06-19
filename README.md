AWS Daily Cost Reporting Email Lambda
This project deploys an AWS Lambda function that automatically generates and sends a daily email summarizing your AWS account's costs. The report provides a clear, at-a-glance overview of spending, including month-to-date totals, daily costs, and a monthly forecast, helping you keep your cloud budget in check.

The function is written in Python and triggered on a daily schedule by Amazon EventBridge.

Features
Automated Daily Emails: Receive a cost report in your inbox at a specific time every day.
Key Cost Metrics:
Month-to-Date Cost: The running total for the current month.
Last 24h Cost: The cost incurred in the last day, showing the daily increase.
Forecasted Monthly Cost: An ML-based prediction of the total bill for the month.
Detailed Breakdown: A service-by-service list of costs, sorted from highest to lowest.
Visual Cost Distribution: A simple bar chart within the email helps you instantly identify the highest-spending services.
Serverless and Efficient: Runs on AWS Lambda, so you only pay for the few seconds it runs each day.
Easily Configurable: Uses Lambda environment variables for easy changes to sender/recipient emails without touching the code.
Final Output
The generated email will look like this:

Prerequisites
Before you begin, ensure you have the following:

An AWS Account.
IAM permissions to create Roles, Policies, Lambda functions, and EventBridge rules.
Verified Email Addresses in Amazon SES. Both the sender and recipient email addresses must be verified in the AWS Region you are deploying this function to (e.g., ap-southeast-1).
Setup and Deployment
Follow these steps to deploy the cost reporter in your AWS account.

Step 1: Create the IAM Policy and Role
The Lambda function needs specific permissions to access AWS services.

Create the IAM Policy:

Navigate to the IAM service in the AWS Console.
Go to Policies and click Create policy.
Switch to the JSON tab and paste the policy text from the IAM_Policy.json section below.
<!-- end list -->

Name the policy something descriptive, like LambdaCostReporterPolicy.
Create the IAM Role:

Navigate to Roles in IAM and click Create role.
Select AWS service as the trusted entity type, and choose Lambda as the use case.
<!-- end list -->

On the permissions page, search for and attach two policies:
The LambdaCostReporterPolicy you just created.
The AWS managed policy named AWSLambdaBasicExecutionRole (this allows the function to write logs to CloudWatch).
Name the role something descriptive, like CostEmailRole, and create it.
Step 2: Create the Lambda Function
Navigate to the Lambda service in the AWS Console.
Click Create function.
Select Author from scratch.
Function name: DailyAWSCostReporter.
Runtime: Select Python 3.12 (or another recent Python version).
Architecture: x86_64.
Permissions: Expand "Change default execution role" and select Use an existing role. Choose the CostEmailRole you created in the previous step.
Click Create function.
Step 3: Configure the Lambda Function
Paste the Code: In the "Code source" section, paste the entire contents of the lambda_function.py file provided below. Click the Deploy button to save your code.

Add Environment Variables:

Go to the Configuration tab, then Environment variables, and click Edit.
Add two variables:
Key: SENDER_EMAIL, Value: your-verified-sender@example.com
Key: RECIPIENT_EMAIL, Value: your-recipient@example.com
Click Save.
Adjust General Configuration:

Go to the Configuration tab, then General configuration, and click Edit.
Set the Timeout to 30 seconds.
Set the Memory to 256 MB.
Click Save.
Step 4: Create the EventBridge Trigger
From your Lambda function's main page, click + Add trigger.
Select EventBridge (CloudWatch Events) as the source.
Choose Create a new rule.
Rule name: RunDailyCostReporter.
Schedule expression: Select Schedule expression and enter a cron expression. EventBridge uses UTC time.
Example: To run at 9:00 AM in Dhaka (UTC+6), you must set the schedule for 3:00 AM UTC. The expression is: cron(0 3 * * ? *)
Click Add.
Your daily cost reporter is now fully deployed and will run automatically on the schedule you defined.