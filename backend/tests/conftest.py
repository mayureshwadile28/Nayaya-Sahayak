"""Test fixtures for Nyaya Sahayak backend tests."""

import os

# Set a dummy API key for tests so that GeminiService doesn't fail on init
os.environ["GEMINI_API_KEY"] = "dummy_key_for_testing"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_rental_text() -> str:
    """Sample rental agreement text for testing."""
    return """
    RENTAL AGREEMENT

    This Rental Agreement is made between Mr. Rajesh Kumar (Landlord/Lessor)
    and Ms. Priya Sharma (Tenant/Lessee) on 1st January 2024.

    Property: Flat No. 301, Green Apartments, MG Road, Bangalore, Karnataka.

    1. MONTHLY RENT: The tenant shall pay a monthly rent of Rs. 25,000 (Rupees
    Twenty Five Thousand only) on or before the 5th of each month.

    2. SECURITY DEPOSIT: The tenant has paid a security deposit of 6 months rent
    (Rs. 1,50,000) which shall be refunded upon vacating the premises.

    3. LOCK-IN PERIOD: This agreement has a lock-in period of 18 months during
    which neither party can terminate the agreement.

    4. NOTICE PERIOD: Either party must provide a notice period of 2 months before
    terminating this agreement.

    5. MAINTENANCE: The tenant shall be responsible for all maintenance and repairs
    including structural repairs to the property.

    6. EVICTION: The landlord reserves the right to evict the tenant immediately
    at his sole discretion without providing any reason.

    7. RENT ESCALATION: The rent shall be increased by 15% at the end of every
    11 months.

    8. DEPOSIT FORFEITURE: In case of any damage to the property, the landlord
    may forfeit the entire security deposit.

    Contact: Rajesh Kumar, Phone: 9876543210, Email: rajesh@example.com
    Aadhaar: 2345 6789 0123, PAN: ABCDE1234F
    """


@pytest.fixture
def sample_employment_text() -> str:
    """Sample employment agreement text for testing."""
    return """
    EMPLOYMENT AGREEMENT

    This Employment Agreement is entered into between TechCorp India Pvt. Ltd.
    (Company) and Mr. Amit Patel (Employee) effective from March 15, 2024.

    1. COMPENSATION: The employee shall receive an annual CTC of Rs. 12,00,000
    (Rupees Twelve Lakhs only) payable monthly.

    2. PROBATION PERIOD: The employee shall be on probation for a period of
    9 months during which employment may be terminated with 7 days notice.

    3. NON-COMPETE: The employee agrees not to work for any competitor for a
    period of 24 months after leaving the company, within India.

    4. TERMINATION: The company may terminate the employee without cause at
    any time by providing immediate notice.

    5. NOTICE PERIOD: The employee must serve a notice period of 90 days.

    6. INTELLECTUAL PROPERTY: All work product, inventions, and intellectual
    property created by the employee shall belong to the company, including
    personal projects developed during the term of employment.
    """


@pytest.fixture
def sample_consumer_text() -> str:
    """Sample consumer complaint text for testing."""
    return """
    CONSUMER COMPLAINT NOTICE

    To: XYZ Electronics Pvt. Ltd.

    Subject: Defective Product - Laptop Model ABC-500

    I, Sunita Verma, purchased a laptop (Model ABC-500) from your e-commerce
    platform on 10th October 2023 for Rs. 75,000.

    The product has a manufacturing defect - the screen has dead pixels and the
    battery does not hold charge for more than 30 minutes. I reported the defect
    within 24 hours of delivery.

    Your refund policy states: "No refund will be provided after delivery.
    All sales are final and non-refundable."

    The warranty shall be void if any unauthorized third-party modification
    is made to the device.

    I demand a full refund of Rs. 75,000 and compensation of Rs. 25,000 for
    mental agony and harassment. This notice is being sent before filing a
    complaint at the Consumer Forum.

    Jurisdiction: Only the courts in Mumbai shall have exclusive jurisdiction.

    The product must be returned within 48 hours of this notice failing which
    the warranty will be cancelled.
    """


@pytest.fixture
def client() -> TestClient:
    """Create a test client that doesn't run the full lifespan."""
    from fastapi import FastAPI

    from app.routes import documents, export, rights

    test_app = FastAPI()
    test_app.include_router(documents.router, prefix="/api")
    test_app.include_router(rights.router, prefix="/api")
    test_app.include_router(export.router, prefix="/api")

    return TestClient(test_app)
