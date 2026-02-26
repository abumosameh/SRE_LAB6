# main.tf
# Terraform configuration to deploy the resilient API for Lab 6.
# Note: This is designed to work within the limitations of AWS Academy Learner Labs.

provider "aws" {
  region = "us-east-1" # Update this to us-west-2 if your Learner Lab requires it
}

# ---------------------------------------------------------------------------
# IAM Role (Using the pre-existing AWS Academy LabRole)
# ---------------------------------------------------------------------------
data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

# ---------------------------------------------------------------------------
# Lambda Source Code Archive
# ---------------------------------------------------------------------------
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "lambda_api.py"
  output_path = "lambda_api.zip"
}

# ---------------------------------------------------------------------------
# Lambda Functions
# ---------------------------------------------------------------------------
resource "aws_lambda_function" "healthy_lambda" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "Lab6-HealthyEndpoint"
  role             = data.aws_iam_role.lab_role.arn
  handler          = "lambda_api.healthy_handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
}

resource "aws_lambda_function" "unreliable_lambda" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "Lab6-UnreliableEndpoint"
  role             = data.aws_iam_role.lab_role.arn
  handler          = "lambda_api.unreliable_handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
}

resource "aws_lambda_function" "slow_lambda" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "Lab6-SlowEndpoint"
  role             = data.aws_iam_role.lab_role.arn
  handler          = "lambda_api.slow_handler"
  runtime          = "python3.12"
  timeout          = 15 # Extended timeout for the slow endpoint
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
}

# ---------------------------------------------------------------------------
# API Gateway
# ---------------------------------------------------------------------------
resource "aws_api_gateway_rest_api" "resiliency_api" {
  name        = "ResiliencyLabAPI"
  description = "API for testing resiliency patterns in Lab 6"
}

# Healthy Endpoint Configuration
resource "aws_api_gateway_resource" "healthy_resource" {
  rest_api_id = aws_api_gateway_rest_api.resiliency_api.id
  parent_id   = aws_api_gateway_rest_api.resiliency_api.root_resource_id
  path_part   = "healthy"
}
resource "aws_api_gateway_method" "healthy_method" {
  rest_api_id   = aws_api_gateway_rest_api.resiliency_api.id
  resource_id   = aws_api_gateway_resource.healthy_resource.id
  http_method   = "GET"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "healthy_integration" {
  rest_api_id             = aws_api_gateway_rest_api.resiliency_api.id
  resource_id             = aws_api_gateway_resource.healthy_resource.id
  http_method             = aws_api_gateway_method.healthy_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.healthy_lambda.invoke_arn
}

# Unreliable Endpoint Configuration
resource "aws_api_gateway_resource" "unreliable_resource" {
  rest_api_id = aws_api_gateway_rest_api.resiliency_api.id
  parent_id   = aws_api_gateway_rest_api.resiliency_api.root_resource_id
  path_part   = "unreliable"
}
resource "aws_api_gateway_method" "unreliable_method" {
  rest_api_id   = aws_api_gateway_rest_api.resiliency_api.id
  resource_id   = aws_api_gateway_resource.unreliable_resource.id
  http_method   = "GET"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "unreliable_integration" {
  rest_api_id             = aws_api_gateway_rest_api.resiliency_api.id
  resource_id             = aws_api_gateway_resource.unreliable_resource.id
  http_method             = aws_api_gateway_method.unreliable_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.unreliable_lambda.invoke_arn
}

# Slow Endpoint Configuration
resource "aws_api_gateway_resource" "slow_resource" {
  rest_api_id = aws_api_gateway_rest_api.resiliency_api.id
  parent_id   = aws_api_gateway_rest_api.resiliency_api.root_resource_id
  path_part   = "slow"
}
resource "aws_api_gateway_method" "slow_method" {
  rest_api_id   = aws_api_gateway_rest_api.resiliency_api.id
  resource_id   = aws_api_gateway_resource.slow_resource.id
  http_method   = "GET"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "slow_integration" {
  rest_api_id             = aws_api_gateway_rest_api.resiliency_api.id
  resource_id             = aws_api_gateway_resource.slow_resource.id
  http_method             = aws_api_gateway_method.slow_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.slow_lambda.invoke_arn
}

# ---------------------------------------------------------------------------
# Lambda Permissions for API Gateway
# ---------------------------------------------------------------------------
resource "aws_lambda_permission" "apigw_healthy" {
  statement_id  = "AllowAPIGatewayInvokeHealthy"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.healthy_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.resiliency_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "apigw_unreliable" {
  statement_id  = "AllowAPIGatewayInvokeUnreliable"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.unreliable_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.resiliency_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "apigw_slow" {
  statement_id  = "AllowAPIGatewayInvokeSlow"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slow_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.resiliency_api.execution_arn}/*/*"
}

# ---------------------------------------------------------------------------
# API Gateway Deployment
# ---------------------------------------------------------------------------
resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.resiliency_api.id

  depends_on = [
    aws_api_gateway_integration.healthy_integration,
    aws_api_gateway_integration.unreliable_integration,
    aws_api_gateway_integration.slow_integration
  ]
}

resource "aws_api_gateway_stage" "api_stage" {
  deployment_id = aws_api_gateway_deployment.api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.resiliency_api.id
  stage_name    = "dev"
}

output "api_base_url" {
  value       = aws_api_gateway_stage.api_stage.invoke_url
  description = "The base URL for our deployed API Gateway"
}
