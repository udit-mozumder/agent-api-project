import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header, Request, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, ValidationError
from typing import Optional, List
from threading import Lock

API_KEY = "supersecretkey"  # In production, use env var/config
CUSTOMERS = {}
CUSTOMERS_LOCK = Lock()

app = FastAPI(title="Customer Management API", version="1.0.0")

# CORS for local dev/testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def api_key_auth(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

class CustomerBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None

class CustomerCreate(CustomerBase):
    first_name: str = Field(...)
    last_name: str = Field(...)
    email: EmailStr = Field(...)

class CustomerUpdate(BaseModel):
    phone: Optional[str] = None
    company: Optional[str] = None

class Customer(CustomerBase):
    id: str
    created_at: str

class CustomerListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[Customer]

class MessageResponse(BaseModel):
    message: str

class ErrorResponse(BaseModel):
    error: str

@app.exception_handler(HTTPException)
def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

@app.exception_handler(ValidationError)
def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": exc.errors()},
    )

@app.get("/health", response_model=dict, tags=["Health"])
def health():
    return {"status": "healthy"}

@app.post("/customers", response_model=Customer, status_code=201, responses={401: {"model": ErrorResponse}}, tags=["Customers"])
def create_customer(customer: CustomerCreate, x_api_key: str = Depends(api_key_auth)):
    customer_id = f"cust_{str(uuid.uuid4())[:8]}"
    now = datetime.utcnow().isoformat() + "Z"
    cust = Customer(
        id=customer_id,
        first_name=customer.first_name,
        last_name=customer.last_name,
        email=customer.email,
        phone=customer.phone,
        company=customer.company,
        created_at=now,
    )
    with CUSTOMERS_LOCK:
        CUSTOMERS[customer_id] = cust
    return cust

@app.get("/customers/{customer_id}", response_model=Customer, responses={404: {"model": ErrorResponse}, 401: {"model": ErrorResponse}}, tags=["Customers"])
def get_customer(customer_id: str, x_api_key: str = Depends(api_key_auth)):
    with CUSTOMERS_LOCK:
        cust = CUSTOMERS.get(customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust

@app.put("/customers/{customer_id}", response_model=MessageResponse, responses={404: {"model": ErrorResponse}, 401: {"model": ErrorResponse}}, tags=["Customers"])
def update_customer(customer_id: str, update: CustomerUpdate, x_api_key: str = Depends(api_key_auth)):
    with CUSTOMERS_LOCK:
        cust = CUSTOMERS.get(customer_id)
        if not cust:
            raise HTTPException(status_code=404, detail="Customer not found")
        data = cust.dict()
        if update.phone is not None:
            data["phone"] = update.phone
        if update.company is not None:
            data["company"] = update.company
        updated = Customer(**data)
        CUSTOMERS[customer_id] = updated
    return {"message": "Customer updated successfully"}

@app.delete("/customers/{customer_id}", response_model=MessageResponse, responses={404: {"model": ErrorResponse}, 401: {"model": ErrorResponse}}, tags=["Customers"])
def delete_customer(customer_id: str, x_api_key: str = Depends(api_key_auth)):
    with CUSTOMERS_LOCK:
        if customer_id not in CUSTOMERS:
            raise HTTPException(status_code=404, detail="Customer not found")
        del CUSTOMERS[customer_id]
    return {"message": "Customer deleted successfully"}

@app.get("/customers", response_model=CustomerListResponse, responses={401: {"model": ErrorResponse}}, tags=["Customers"])
def list_customers(
    page: int = 1,
    page_size: int = 10,
    email: Optional[str] = None,
    company: Optional[str] = None,
    x_api_key: str = Depends(api_key_auth),
):
    with CUSTOMERS_LOCK:
        customers = list(CUSTOMERS.values())
    # Filtering
    if email:
        customers = [c for c in customers if c.email == email]
    if company:
        customers = [c for c in customers if c.company == company]
    total = len(customers)
    start = (page - 1) * page_size
    end = start + page_size
    data = customers[start:end]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": data,
    }
