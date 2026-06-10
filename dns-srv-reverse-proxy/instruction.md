Build a dynamic reverse proxy that discovers and routes traffic to backend services using DNS SRV records, with health checking and automatic failover.

## Technical Requirements

- Python 3.x for the reverse proxy implementation
- dnsmasq for DNS service discovery
- Mock backend services listening on ports 8001-8004
- Reverse proxy listening on port 8000

## Implementation Specifications

**DNS Configuration:**
- Configure dnsmasq with SRV records in `/app/dnsmasq.conf`
- Service domain: `_http._tcp.services.local`
- SRV record format: priority, weight, port, hostname
- Example: `srv-host=_http._tcp.services.local,backend1.local,8001,10,50`

**Backend Services:**
- Create 4 mock HTTP services on ports 8001, 8002, 8003, 8004
- Each service must respond to GET `/health` with JSON: `{"status": "healthy", "service": "backend1"}`
- Each service must respond to GET `/` with JSON: `{"message": "Response from backend1", "port": 8001}`

**Reverse Proxy (`/app/proxy.py`):**
- Query DNS SRV records to discover available backends
- Distribute incoming requests across healthy backends
- Perform health checks every 5 seconds on `/health` endpoint
- Remove unhealthy backends from rotation automatically
- Return 503 Service Unavailable if no healthy backends exist

**Client Script (`/app/client.py`):**
- Send HTTP GET requests to `http://localhost:8000/`
- Accept command-line argument for number of requests (default: 10)
- Output response data showing which backend handled each request

## Expected Behavior

1. Proxy discovers backends via DNS SRV queries
2. Health checks run continuously in background
3. Requests are distributed among healthy backends
4. When a backend fails health check, it's removed from rotation
5. When a failed backend recovers, it's added back to rotation
6. Client receives responses from different backends demonstrating load distribution
