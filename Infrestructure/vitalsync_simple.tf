# ============================================================================
# VITALSYNC - ARQUITECTURA SIMPLIFICADA
# 1 EC2 + Docker Compose + RDS existente + CodePipeline
# ============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project   = "VitalSync"
      ManagedBy = "Terraform"
    }
  }
}

# ============================================================================
# VARIABLES
# ============================================================================

variable "aws_region" {
  default = "us-east-1"
}

variable "db_host" {
  description = "RDS endpoint existente"
  default     = "database-1.cfwgyw8m2myn.us-east-1.rds.amazonaws.com"
}

variable "db_name" {
  default = "vitalsync"
}

variable "db_username" {
  sensitive = true
}

variable "db_password" {
  sensitive = true
}

variable "jwt_secret" {
  sensitive = true
}

variable "github_repo" {
  description = "GitHub repo (owner/repo)"
  default     = "Itsmasca/HealthIA"
}

variable "github_branch" {
  default = "master"
}

variable "key_pair_name" {
  description = "Nombre del key pair para SSH"
  default     = "vitalsync-key"
}

# ============================================================================
# DATA
# ============================================================================

data "aws_caller_identity" "current" {}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# AMI dinámica - Amazon Linux 2023 más reciente
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ============================================================================
# SECURITY GROUP
# ============================================================================

resource "aws_security_group" "vitalsync" {
  name        = "vitalsync-ec2-sg"
  description = "Security group for VitalSync EC2"
  vpc_id      = data.aws_vpc.default.id
  
  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # VitalSync API (REST + GraphQL en puerto 8000)
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "VitalSync FastAPI (REST + GraphQL)"
  }
  
  # Node-RED
  ingress {
    from_port   = 1880
    to_port     = 1880
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # HTTP (opcional para nginx)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = { Name = "vitalsync-sg" }
}

# ============================================================================
# IAM ROLE PARA EC2 (acceso a ECR, SSM, CodeDeploy)
# ============================================================================

resource "aws_iam_role" "ec2_role" {
  name = "vitalsync-ec2-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "codedeploy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforAWSCodeDeploy"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "vitalsync-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# ============================================================================
# EC2 INSTANCE
# ============================================================================

resource "aws_instance" "vitalsync" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = "t3.medium"
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.vitalsync.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  
  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }
  
  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -e
    
    # Update system
    yum update -y
    
    # Install Docker
    yum install -y docker
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ec2-user
    
    # Install Docker Compose
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # Install CodeDeploy Agent
    yum install -y ruby wget
    cd /home/ec2-user
    wget https://aws-codedeploy-${var.aws_region}.s3.${var.aws_region}.amazonaws.com/latest/install
    chmod +x ./install
    ./install auto
    systemctl start codedeploy-agent
    systemctl enable codedeploy-agent
    
    # Install Git
    yum install -y git
    
    # Create app directory with hostPath volumes
    mkdir -p /opt/vitalsync
    mkdir -p /opt/vitalsync/nodered-data
    mkdir -p /opt/vitalsync/postgres-data
    chown -R ec2-user:ec2-user /opt/vitalsync
    
    # Create .env file (variables según Settings.py de VitalSync)
    cat > /opt/vitalsync/.env <<ENVFILE
DATABASE_HOST=${var.db_host}
DATABASE_PORT=5432
DATABASE_NAME=${var.db_name}
DATABASE_USER=${var.db_username}
DATABASE_PASSWORD=${var.db_password}
HOST=0.0.0.0
PORT=8000
DEBUG=false
JWT_SECRET=${var.jwt_secret}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
ENVFILE
    
    # Login to ECR
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com
    
    echo "Setup complete!"
  EOF
  )
  
  tags = {
    Name = "vitalsync-server"
  }
}

# Elastic IP para IP fija
resource "aws_eip" "vitalsync" {
  instance = aws_instance.vitalsync.id
  domain   = "vpc"
  
  tags = { Name = "vitalsync-eip" }
}

# ============================================================================
# ECR REPOSITORIES
# ============================================================================

resource "aws_ecr_repository" "api" {
  name = "vitalsync/api"
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_ecr_repository" "nodered" {
  name = "vitalsync/nodered"
  image_scanning_configuration { scan_on_push = true }
}

# ============================================================================
# CODEDEPLOY
# ============================================================================

resource "aws_codedeploy_app" "vitalsync" {
  name             = "vitalsync"
  compute_platform = "Server"
}

resource "aws_codedeploy_deployment_group" "vitalsync" {
  app_name              = aws_codedeploy_app.vitalsync.name
  deployment_group_name = "vitalsync-deploy-group"
  service_role_arn      = aws_iam_role.codedeploy_role.arn
  
  deployment_config_name = "CodeDeployDefault.OneAtATime"
  
  ec2_tag_set {
    ec2_tag_filter {
      key   = "Name"
      type  = "KEY_AND_VALUE"
      value = "vitalsync-server"
    }
  }
  
  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE"]
  }
}

resource "aws_iam_role" "codedeploy_role" {
  name = "vitalsync-codedeploy-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "codedeploy.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "codedeploy_policy" {
  role       = aws_iam_role.codedeploy_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole"
}

# ============================================================================
# CODEPIPELINE
# ============================================================================

resource "aws_s3_bucket" "pipeline" {
  bucket = "vitalsync-pipeline-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "pipeline" {
  bucket = aws_s3_bucket.pipeline.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_codestarconnections_connection" "github" {
  name          = "vitalsync-github"
  provider_type = "GitHub"
}

# IAM for Pipeline
resource "aws_iam_role" "pipeline" {
  name = "vitalsync-pipeline-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "codepipeline.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "pipeline" {
  name = "pipeline-policy"
  role = aws_iam_role.pipeline.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:*"]
        Resource = ["${aws_s3_bucket.pipeline.arn}", "${aws_s3_bucket.pipeline.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["codebuild:*"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["codedeploy:*"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["codestar-connections:UseConnection"]
        Resource = aws_codestarconnections_connection.github.arn
      }
    ]
  })
}

# IAM for CodeBuild
resource "aws_iam_role" "codebuild" {
  name = "vitalsync-codebuild-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "codebuild.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "codebuild" {
  name = "codebuild-policy"
  role = aws_iam_role.codebuild.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["logs:*"], Resource = "*" },
      { Effect = "Allow", Action = ["s3:*"], Resource = ["${aws_s3_bucket.pipeline.arn}", "${aws_s3_bucket.pipeline.arn}/*"] },
      { Effect = "Allow", Action = ["ecr:*"], Resource = "*" }
    ]
  })
}

# CodeBuild Project
resource "aws_codebuild_project" "vitalsync" {
  name         = "vitalsync-build"
  service_role = aws_iam_role.codebuild.arn
  
  artifacts { type = "CODEPIPELINE" }
  
  environment {
    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type            = "LINUX_CONTAINER"
    privileged_mode = true
    
    environment_variable { name = "AWS_ACCOUNT_ID", value = data.aws_caller_identity.current.account_id }
    environment_variable { name = "AWS_REGION", value = var.aws_region }
    environment_variable { name = "ECR_REPO_API", value = aws_ecr_repository.api.repository_url }
    environment_variable { name = "ECR_REPO_NODERED", value = aws_ecr_repository.nodered.repository_url }
  }
  
  source {
    type      = "CODEPIPELINE"
    buildspec = <<-EOF
      version: 0.2
      phases:
        pre_build:
          commands:
            - echo Logging in to ECR...
            - aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
            - IMAGE_TAG=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
        build:
          commands:
            - echo Building VitalSync API image...
            - docker build -t $ECR_REPO_API:latest -t $ECR_REPO_API:$IMAGE_TAG -f Dockerfile .
            - echo Building Node-RED image...
            - docker build -t $ECR_REPO_NODERED:latest -t $ECR_REPO_NODERED:$IMAGE_TAG -f Node-Red/Dockerfile ./Node-Red || echo "Using base nodered image"
        post_build:
          commands:
            - echo Pushing images...
            - docker push $ECR_REPO_API:latest
            - docker push $ECR_REPO_API:$IMAGE_TAG
            - docker push $ECR_REPO_NODERED:latest || true
            - docker push $ECR_REPO_NODERED:$IMAGE_TAG || true
            - echo Done!
      artifacts:
        files:
          - '**/*'
    EOF
  }
}

# CodePipeline
resource "aws_codepipeline" "vitalsync" {
  name     = "vitalsync-pipeline"
  role_arn = aws_iam_role.pipeline.arn
  
  artifact_store {
    location = aws_s3_bucket.pipeline.bucket
    type     = "S3"
  }
  
  stage {
    name = "Source"
    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source"]
      configuration = {
        ConnectionArn    = aws_codestarconnections_connection.github.arn
        FullRepositoryId = var.github_repo
        BranchName       = var.github_branch
      }
    }
  }
  
  stage {
    name = "Build"
    action {
      name             = "Build"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      version          = "1"
      input_artifacts  = ["source"]
      output_artifacts = ["build"]
      configuration    = { ProjectName = aws_codebuild_project.vitalsync.name }
    }
  }
  
  stage {
    name = "Deploy"
    action {
      name            = "Deploy"
      category        = "Deploy"
      owner           = "AWS"
      provider        = "CodeDeploy"
      version         = "1"
      input_artifacts = ["build"]
      configuration = {
        ApplicationName     = aws_codedeploy_app.vitalsync.name
        DeploymentGroupName = aws_codedeploy_deployment_group.vitalsync.deployment_group_name
      }
    }
  }
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "ec2_public_ip" {
  value = aws_eip.vitalsync.public_ip
}

output "endpoints" {
  value = {
    api      = "http://${aws_eip.vitalsync.public_ip}:8000"
    rest_api = "http://${aws_eip.vitalsync.public_ip}:8000/api"
    graphql  = "http://${aws_eip.vitalsync.public_ip}:8000/graphql"
    health   = "http://${aws_eip.vitalsync.public_ip}:8000/api/health"
    nodered  = "http://${aws_eip.vitalsync.public_ip}:1880"
  }
}

output "ssh_command" {
  value = "ssh -i ${var.key_pair_name}.pem ec2-user@${aws_eip.vitalsync.public_ip}"
}

output "ecr_repos" {
  value = {
    api     = aws_ecr_repository.api.repository_url
    nodered = aws_ecr_repository.nodered.repository_url
  }
}

output "rds_connection" {
  value = "postgresql://${var.db_username}:****@${var.db_host}:5432/${var.db_name}"
}

output "github_connection_notice" {
  value = "⚠️ Aprobar conexión GitHub: https://console.aws.amazon.com/codesuite/settings/connections"
}
