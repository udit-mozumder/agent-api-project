import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Header, Depends, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

API_KEY = "supersecretkey"  # For demo; in production, use env vars or secrets manager

app = FastAPI(title="Customer Management API")

# In-memory DB substitute
CUSTOMERS = {}

# --------- Models ---------
class CustomerBase(BaseModel):
    first_name: Optional[str] = Field(None, example="John")
    last_name: Optional[str] = Field(None, example="Doe")
    email: Optional[EmailStr] = Field(None, example="john@example.com")
    phone: Optional[str] = Field(None, example="9876543210")
    company: Optional[str] = Field(None, example="Acme Inc")

class CustomerCreate(CustomerBase):
    first_name: str
    last_name: str
    email: EmailStr

class CustomerUpdate(BaseModel):
    phone: Optional[str] = None
    company: Optional[str] = None

class Customer(CustomerBase):
    id: str
    created_at: datetime

class CustomerListOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    company: Optional[str] = None

class CustomerListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[CustomerListOut]

# --------- Authentication Dependency ---------
def api_key_auth(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

# --------- Error Handler ---------
@app.exception_handler(HTTPException)
def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

# --------- Endpoints ---------
@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}

@app.post("/customers", status_code=201, response_model=Customer, tags=["Customers"])
def create_customer(
    customer: CustomerCreate,
    _: None = Depends(api_key_auth),
):
    # Email must be unique
    for c in CUSTOMERS.values():
        if c.email == customer.email:
            raise HTTPException(status_code=400, detail="Email already exists")
    cust_id = f"cust_{str(uuid.uuid4())[:8]}"
    created_at = datetime.utcnow()
    customer_obj = Customer(
        id=cust_id,
        created_at=created_at,
        **customer.dict(),
    )
    CUSTOMERS[cust_id] = customer_obj
    return customer_obj

@app.get("/customers/{customer_id}", response_model=Customer, tags=["Customers"])
def get_customer(customer_id: str, _: None = Depends(api_key_auth)):
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@app.put("/customers/{customer_id}", tags=["Customers"])
def update_customer(
    customer_id: str,
    update: CustomerUpdate,
    _: None = Depends(api_key_auth),
):
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    update_data = update.dict(exclude_unset=True)
    for k, v in update_data.items():
        setattr(customer, k, v)
    CUSTOMERS[customer_id] = customer
    return {"message": "Customer updated successfully"}

@app.delete("/customers/{customer_id}", tags=["Customers"])
def delete_customer(customer_id: str, _: None = Depends(api_key_auth)):
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    del CUSTOMERS[customer_id]
    return {"message": "Customer deleted successfully"}

@app.get("/customers", response_model=CustomerListResponse, tags=["Customers"])
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    email: Optional[str] = None,
    company: Optional[str] = None,
    _: None = Depends(api_key_auth),
):
    customers = list(CUSTOMERS.values())
    # Filtering
    if email:
        customers = [c for c in customers if c.email == email]
    if company:
        customers = [c for c in customers if c.company == company]
    total = len(customers)
    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    customers_page = customers[start:end]
    data = [CustomerListOut(
        id=c.id,
        first_name=c.first_name,
        last_name=c.last_name,
        email=c.email,
        company=c.company,
    ) for c in customers_page]
    return CustomerListResponse(
        total=total,
        page=page,
        page_size=page_size,
        data=data,
    )
