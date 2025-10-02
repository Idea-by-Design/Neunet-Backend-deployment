from fastapi import APIRouter, HTTPException, status
from azure.cosmos import exceptions
from datetime import datetime
import uuid
from .models import UserSignup, UserLogin, TokenResponse, UserResponse, UserInDB, ForgotPasswordRequest, ResetPasswordRequest, UpdatePasswordRequest, SuccessResponse, VerifyIdentityResetRequest
from .auth_utils import get_password_hash, verify_password, create_access_token
from .database import get_users_container

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignup):
    """
    Register a new user
    """
    container = get_users_container()
    
    # Check if user already exists
    query = f"SELECT * FROM c WHERE c.email = '{user_data.email}' OR c.username = '{user_data.username}'"
    try:
        existing_users = list(container.query_items(query=query, enable_cross_partition_query=True))
        if existing_users:
            if any(u['email'] == user_data.email for u in existing_users):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            if any(u['username'] == user_data.username for u in existing_users):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error checking existing users: {e}")
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    now = datetime.utcnow().isoformat()
    
    new_user = {
        "id": user_id,
        "name": user_data.name,
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "company_size": user_data.company_size,
        "created_at": now,
        "updated_at": now
    }
    
    try:
        container.create_item(body=new_user)
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user_data.email, "user_id": user_id})
    
    # Return token and user info
    user_response = UserResponse(
        id=user_id,
        name=user_data.name,
        username=user_data.username,
        email=user_data.email,
        company_size=user_data.company_size,
        created_at=now
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Authenticate user and return access token
    """
    container = get_users_container()
    
    # Find user by email
    query = f"SELECT * FROM c WHERE c.email = '{credentials.email}'"
    try:
        users = list(container.query_items(query=query, enable_cross_partition_query=True))
        if not users:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        user = users[0]
        
        # Verify password
        if not verify_password(credentials.password, user['hashed_password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user['email'], "user_id": user['id']}
        )
        
        # Return token and user info
        user_response = UserResponse(
            id=user['id'],
            name=user['name'],
            username=user['username'],
            email=user['email'],
            company_size=user['company_size'],
            created_at=user['created_at']
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
        
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str):
    """
    Get current user info from token
    """
    from .auth_utils import verify_token
    
    payload = verify_token(token)
    email = payload.get("sub")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    container = get_users_container()
    query = f"SELECT * FROM c WHERE c.email = '{email}'"
    
    try:
        users = list(container.query_items(query=query, enable_cross_partition_query=True))
        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = users[0]
        return UserResponse(
            id=user['id'],
            name=user['name'],
            username=user['username'],
            email=user['email'],
            company_size=user['company_size'],
            created_at=user['created_at']
        )
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post("/forgot-password", response_model=SuccessResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Request password reset - generates a reset token
    Note: In production, this should send an email with the reset link
    For now, it returns the token directly for testing
    """
    container = get_users_container()
    
    # Find user by email
    query = f"SELECT * FROM c WHERE c.email = '{request.email}'"
    try:
        users = list(container.query_items(query=query, enable_cross_partition_query=True))
        if not users:
            # Don't reveal if email exists or not for security
            return SuccessResponse(
                message="If the email exists, a password reset link has been sent"
            )
        
        user = users[0]
        
        # Create a password reset token (valid for 15 minutes)
        from datetime import timedelta
        reset_token = create_access_token(
            data={"sub": user['email'], "user_id": user['id'], "type": "password_reset"},
            expires_delta=timedelta(minutes=15)
        )
        
        # TODO: In production, send email with reset link
        # For now, we'll return the token in the response for testing
        return SuccessResponse(
            message=f"Password reset token (for testing): {reset_token}"
        )
        
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post("/reset-password", response_model=SuccessResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password using the reset token
    """
    from .auth_utils import verify_token
    
    try:
        # Verify the reset token
        payload = verify_token(request.token)
        email = payload.get("sub")
        token_type = payload.get("type")
        
        if not email or token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired reset token"
            )
        
        container = get_users_container()
        
        # Find user
        query = f"SELECT * FROM c WHERE c.email = '{email}'"
        users = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = users[0]
        
        # Update password
        new_hashed_password = get_password_hash(request.new_password)
        user['hashed_password'] = new_hashed_password
        user['updated_at'] = datetime.utcnow().isoformat()
        
        # Save to database
        container.replace_item(item=user['id'], body=user)
        
        return SuccessResponse(message="Password reset successfully")
        
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post("/update-password", response_model=SuccessResponse)
async def update_password(request: UpdatePasswordRequest, token: str):
    """
    Update password for authenticated user
    Requires current password verification
    """
    from .auth_utils import verify_token
    
    # Verify the access token
    payload = verify_token(token)
    email = payload.get("sub")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    container = get_users_container()
    
    # Find user
    query = f"SELECT * FROM c WHERE c.email = '{email}'"
    try:
        users = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = users[0]
        
        # Verify current password
        if not verify_password(request.current_password, user['hashed_password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # Update to new password
        new_hashed_password = get_password_hash(request.new_password)
        user['hashed_password'] = new_hashed_password
        user['updated_at'] = datetime.utcnow().isoformat()
        
        # Save to database
        container.replace_item(item=user['id'], body=user)
        
        return SuccessResponse(message="Password updated successfully")
        
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post("/reset-password-verify-identity", response_model=SuccessResponse)
async def reset_password_verify_identity(request: VerifyIdentityResetRequest):
    """
    Reset password by verifying user identity (username, email, name)
    No email required - alternative to forgot password flow
    """
    container = get_users_container()
    
    # Find user by email
    query = f"SELECT * FROM c WHERE c.email = '{request.email}'"
    try:
        users = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        if not users:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not verify identity. Please check your information."
            )
        
        user = users[0]
        
        # Verify all identity fields match
        if (user['username'].lower() != request.username.lower() or 
            user['name'].lower() != request.name.lower()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not verify identity. Please check your information."
            )
        
        # All identity checks passed - update password
        new_hashed_password = get_password_hash(request.new_password)
        user['hashed_password'] = new_hashed_password
        user['updated_at'] = datetime.utcnow().isoformat()
        
        # Save to database
        container.replace_item(item=user['id'], body=user)
        
        return SuccessResponse(message="Password reset successfully. You can now log in with your new password.")
        
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
