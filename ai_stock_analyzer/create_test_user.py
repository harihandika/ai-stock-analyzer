import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("."))

from app.infrastructure.database import AsyncSessionLocal
from app.domain.models.models import User
from app.core.security import hash_password

async def create_user():
    email = "admin@test.com"
    password = "password"
    full_name = "Admin User"
    
    async with AsyncSessionLocal() as session:
        # Check if user exists
        from sqlalchemy import select
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalars().first()
        
        if user:
            print(f"User {email} already exists.")
            return
        
        new_user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            subscription_tier="premium",
            is_active=True
        )
        session.add(new_user)
        await session.commit()
        print(f"User created: email={email}, password={password}")

if __name__ == "__main__":
    asyncio.run(create_user())
