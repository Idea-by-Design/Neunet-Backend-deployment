#!/usr/bin/env python3
"""
Script to list all users in the Cosmos DB users container
"""
import asyncio
from services.auth.database import get_users_container

async def list_users():
    """List all users in the database"""
    container = get_users_container()
    
    print("📋 All Users in Database:")
    print("=" * 50)
    
    try:
        # Query all users
        query = "SELECT * FROM c"
        users = list(container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        if not users:
            print("No users found in database")
            return
        
        for i, user in enumerate(users, 1):
            print(f"\n👤 User {i}:")
            print(f"   ID: {user.get('id', 'N/A')}")
            print(f"   Name: {user.get('name', 'N/A')}")
            print(f"   Username: {user.get('username', 'N/A')}")
            print(f"   Email: {user.get('email', 'N/A')}")
            print(f"   Company Size: {user.get('company_size', 'N/A')}")
            print(f"   Created: {user.get('created_at', 'N/A')}")
            print(f"   Updated: {user.get('updated_at', 'N/A')}")
            print(f"   Password Hash: {user.get('hashed_password', 'N/A')[:20]}...")
        
        print(f"\n📊 Total Users: {len(users)}")
        
    except Exception as e:
        print(f"❌ Error querying users: {e}")

if __name__ == "__main__":
    asyncio.run(list_users())
