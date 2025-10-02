from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserSignup(BaseModel):
    """User signup request model"""
    name: str
    username: str
    email: EmailStr
    password: str
    company_size: str

class UserLogin(BaseModel):
    """User login request model"""
    email: EmailStr
    password: str

class UserInDB(BaseModel):
    """User model stored in database"""
    id: str
    name: str
    username: str
    email: EmailStr
    hashed_password: str
    company_size: str
    created_at: str
    updated_at: str

class UserResponse(BaseModel):
    """User response model (without password)"""
    id: str
    name: str
    username: str
    email: EmailStr
    company_size: str
    created_at: str

class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str
    user: UserResponse

class ForgotPasswordRequest(BaseModel):
    """Forgot password request model"""
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    """Reset password request model"""
    token: str
    new_password: str

class UpdatePasswordRequest(BaseModel):
    """Update password request model"""
    current_password: str
    new_password: str

class SuccessResponse(BaseModel):
    """Generic success response model"""
    message: str

class VerifyIdentityResetRequest(BaseModel):
    """Verify identity and reset password request model"""
    username: str
    email: EmailStr
    name: str
    new_password: str
