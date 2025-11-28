# VitalSync API

Family health monitoring system with IoT integration.

---

## Demo Video

Watch the full application demo showcasing the architecture and features:

[![VitalSync Demo](https://img.youtube.com/vi/BeXeFX3lSOw/0.jpg)](https://youtu.be/BeXeFX3lSOw)

**Video Link:** https://youtu.be/BeXeFX3lSOw

The demo covers:
- AWS ECS Fargate deployment architecture
- Node-RED IoT integration with Xiaomi devices
- Real-time vital signs monitoring (heart rate, oxygen level, temperature, steps)
- PostgreSQL RDS database configuration
- Service Discovery and container communication
- Dashboard visualization

---

## AWS ECS Architecture

```
                        VPC
    +--------------------------------------------------+
    |                                                  |
    |   +-------------+      +-------------+           |
    |   |  Node-RED   | ---> | VitalSync   |           |
    |   |  (Fargate)  |      |  API        |           |
    |   |  :1880      |      |  (Fargate)  |           |
    |   +-------------+      |  :8000      |           |
    |                        +------+------+           |
    |                               |                  |
    |                               v                  |
    |                        +-------------+           |
    |                        | PostgreSQL  |           |
    |                        |  (RDS)      |           |
    |                        |  :5432      |           |
    |                        +-------------+           |
    |                                                  |
    +--------------------------------------------------+
```

---

## ECS Fargate Deployment

### 1. Create ECS Cluster

```bash
aws ecs create-cluster \
    --cluster-name vitalsync-cluster \
    --capacity-providers FARGATE \
    --region us-east-1
```

### 2. Create Namespace for Service Discovery

```bash
aws servicediscovery create-private-dns-namespace \
    --name vitalsync.local \
    --vpc vpc-xxxxxxxx \
    --region us-east-1
```

### 3. Create Service Discovery Service

```bash
aws servicediscovery create-service \
    --name api \
    --dns-config "NamespaceId=ns-xxxxxxxx,DnsRecords=[{Type=A,TTL=60}]" \
    --health-check-custom-config FailureThreshold=1
```

### 4. Task Definition - VitalSync API

```json
{
  "family": "vitalsync-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/vitalsync-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "DATABASE_HOST", "value": "vitalsync-db.xxxxxxxx.us-east-1.rds.amazonaws.com"},
        {"name": "DATABASE_PORT", "value": "5432"},
        {"name": "DATABASE_NAME", "value": "vitalsync"},
        {"name": "DATABASE_USER", "value": "postgres"},
        {"name": "DATABASE_PASSWORD", "value": "PASSWORD"},
        {"name": "JWT_SECRET", "value": "SECRET"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/vitalsync-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "api"
        }
      }
    }
  ]
}
```

### 5. Task Definition - Node-RED

```json
{
  "family": "vitalsync-nodered",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "nodered",
      "image": "nodered/node-red:latest",
      "portMappings": [
        {
          "containerPort": 1880,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "API_URL", "value": "http://api.vitalsync.local:8000"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/vitalsync-nodered",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "nodered"
        }
      }
    }
  ]
}
```

### 6. Create ECS Service with Service Discovery

```bash
aws ecs create-service \
    --cluster vitalsync-cluster \
    --service-name vitalsync-api \
    --task-definition vitalsync-api:1 \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
    --service-registries "registryArn=arn:aws:servicediscovery:us-east-1:ACCOUNT:service/srv-xxx"
```

---

## ECS Container Communication

### DNS Service Discovery

When using Service Discovery in ECS, services are automatically registered with a DNS name:

| Service | Internal DNS |
|---------|--------------|
| API | `api.vitalsync.local` |
| Node-RED | `nodered.vitalsync.local` |

### From Node-RED to API

In Node-RED, configure the HTTP Request node:

```
URL: http://api.vitalsync.local:8000/api/vitals
```

### Security Groups

**SG for API (sg-api):**
```
Inbound:
- Port 8000 from sg-nodered
- Port 8000 from ALB (if used)

Outbound:
- Port 5432 to sg-rds
- Port 443 to 0.0.0.0/0 (ECR)
```

**SG for Node-RED (sg-nodered):**
```
Inbound:
- Port 1880 from your IP or ALB

Outbound:
- Port 8000 to sg-api
```

**SG for RDS (sg-rds):**
```
Inbound:
- Port 5432 from sg-api
```

---

## API Endpoints

### REST

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Current user |
| POST | `/api/auth/refresh` | Refresh token |
| POST | `/api/vitals` | Send vital signs |
| GET | `/health` | Health check |

### GraphQL

Endpoint: `POST /graphql`

---

## Usage from Node-RED

### Login

```json
{
  "email": "user@vitalsync.com",
  "password": "password123"
}
```

POST to `http://api.vitalsync.local:8000/api/auth/login`

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Send Vitals

```json
{
  "device_id": "XIAOMI-001",
  "heart_rate": 72,
  "oxygen_level": 98.5,
  "body_temperature": 36.5,
  "steps": 5000
}
```

POST to `http://api.vitalsync.local:8000/api/vitals`

Headers:
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| DATABASE_HOST | RDS Endpoint | `xxx.rds.amazonaws.com` |
| DATABASE_PORT | DB Port | `5432` |
| DATABASE_NAME | DB Name | `vitalsync` |
| DATABASE_USER | DB User | `postgres` |
| DATABASE_PASSWORD | DB Password | `secret` |
| JWT_SECRET | JWT Key | `secret-key` |
| DEBUG | Debug mode | `false` |

---

## Dashboard

The dashboard for visualizing vital signs data is available at:

**URL:** https://vital-sync-dashboard.vercel.app/

**Access Credentials:**
| Field | Value |
|-------|-------|
| User | kikemc769@gmail.com |
| Password | 123456 |

---

## Troubleshooting

### Error 422 on /api/vitals

Payload must have this exact format:
```json
{
  "device_id": "string",
  "heart_rate": 72,
  "oxygen_level": 98.5,
  "body_temperature": 36.5,
  "steps": 5000
}
```

### Node-RED not connecting to API

1. Verify both services are in the same VPC
2. Verify Security Groups allow traffic
3. Verify Service Discovery is configured
4. Test DNS: `nslookup api.vitalsync.local`

### RDS Connection Error

1. Verify RDS Security Group allows port 5432 from ECS
2. Verify RDS is in the same VPC
3. Verify credentials in environment variables
