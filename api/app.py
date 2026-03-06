import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Header, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

API_KEY = "my-secret-key"  # In production, use secure storage

def api_key_auth(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

app = FastAPI()

# In-memory DB
CUSTOMERS = {}

class CustomerBase(BaseModel):
    first_name: str = Field(...)
    last_name: str = Field(...)
    email: EmailStr = Field(...)
    phone: Optional[str] = None
    company: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    phone: Optional[str] = None
    company: Optional[str] = None

class Customer(CustomerBase):
    id: str
    created_at: datetime

class CustomerListItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    company: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/customers", response_model=Customer, status_code=201, responses={401: {"model": None, "description": "Invalid API Key"}})
def create_customer(customer: CustomerCreate, x_api_key: str = Depends(api_key_auth)):
    customer_id = f"cust_{str(uuid.uuid4())[:8]}"
    created_at = datetime.utcnow()
    data = customer.dict()
    new_customer = {
        "id": customer_id,
        "created_at": created_at,
        **data
    }
    CUSTOMERS[customer_id] = new_customer
    return new_customer

@app.get("/customers/{customer_id}", response_model=Customer)
def get_customer(customer_id: str, x_api_key: str = Depends(api_key_auth)):
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        return JSONResponse(status_code=404, content={"error": "Customer not found"})
    return customer

@app.put("/customers/{customer_id}")
def update_customer(customer_id: str, update: CustomerUpdate, x_api_key: str = Depends(api_key_auth)):
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        return JSONResponse(status_code=404, content={"error": "Customer not found"})
    customer.update({k: v for k, v in update.dict().items() if v is not None})
    CUSTOMERS[customer_id] = customer
    return {"message": "Customer updated successfully"}

@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: str, x_api_key: str = Depends(api_key_auth)):
    if customer_id not in CUSTOMERS:
        return JSONResponse(status_code=404, content={"error": "Customer not found"})
    del CUSTOMERS[customer_id]
    return {"message": "Customer deleted successfully"}

@app.get("/customers", response_model=dict)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    email: Optional[str] = None,
    company: Optional[str] = None,
    x_api_key: str = Depends(api_key_auth),
):
    filtered = list(CUSTOMERS.values())
    if email:
        filtered = [c for c in filtered if c["email"] == email]
    if company:
        filtered = [c for c in filtered if c.get("company") == company]
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    data = [CustomerListItem(**c).dict() for c in filtered[start:end]]
    return {"total": total, "page": page, "page_size": page_size, "data": data}

@app.exception_handler(HTTPException)
def custom_http_exception_handler(request, exc):
    if exc.status_code == 401:
        return JSONResponse(status_code=401, content={"error": "Invalid API Key"})
    elif exc.status_code == 404:
        return JSONResponse(status_code=404, content={"error": exc.detail})
    elif exc.status_code == 400:
        return JSONResponse(status_code=400, content={"error": exc.detail})
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
