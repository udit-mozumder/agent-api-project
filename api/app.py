import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Request, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

app = FastAPI()

# In-memory customer storage (for demonstration)
CUSTOMERS: Dict[str, Dict[str, Any]] = {}

API_KEY = "secret_api_key"  # In real usage, use env vars or a DB

# -------------------
# Models
# -------------------
class CustomerCreate(BaseModel):
    first_name: str = Field(...)
    last_name: str = Field(...)
    email: EmailStr = Field(...)
    phone: Optional[str] = None
    company: Optional[str] = None

class CustomerUpdate(BaseModel):
    phone: Optional[str] = None
    company: Optional[str] = None

class Customer(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    created_at: str

class ListCustomersResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[Customer]

# -------------------
# Auth Dependency
# -------------------
def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

# -------------------
# Error Handling
# -------------------
@app.exception_handler(HTTPException)
def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(Exception)
def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": "Internal server error"})

# -------------------
# Endpoints
# -------------------
@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/customers", response_model=Customer, status_code=201, dependencies=[Depends(verify_api_key)])
def create_customer(payload: CustomerCreate):
    customer_id = f"cust_{str(uuid.uuid4())[:8]}"
    now = datetime.utcnow().isoformat() + "Z"
    customer = {
        "id": customer_id,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "email": payload.email,
        "phone": payload.phone,
        "company": payload.company,
        "created_at": now
    }
    CUSTOMERS[customer_id] = customer
    return customer

@app.get("/customers/{customer_id}", response_model=Customer, dependencies=[Depends(verify_api_key)])
def get_customer(customer_id: str):
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@app.put("/customers/{customer_id}", dependencies=[Depends(verify_api_key)])
def update_customer(customer_id: str, payload: CustomerUpdate):
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if payload.phone is not None:
        customer["phone"] = payload.phone
    if payload.company is not None:
        customer["company"] = payload.company
    CUSTOMERS[customer_id] = customer
    return {"message": "Customer updated successfully"}

@app.delete("/customers/{customer_id}", dependencies=[Depends(verify_api_key)])
def delete_customer(customer_id: str):
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    del CUSTOMERS[customer_id]
    return {"message": "Customer deleted successfully"}

@app.get("/customers", response_model=ListCustomersResponse, dependencies=[Depends(verify_api_key)])
def list_customers(
    page: int = 1,
    page_size: int = 10,
    email: Optional[str] = None,
    company: Optional[str] = None
):
    filtered = list(CUSTOMERS.values())
    if email:
        filtered = [c for c in filtered if c["email"] == email]
    if company:
        filtered = [c for c in filtered if c.get("company") == company]
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    data = filtered[start:end]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": data
    }
