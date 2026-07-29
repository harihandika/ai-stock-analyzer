import asyncio
import os
import sys

# Tambahkan path agar bisa mengimpor module dari app/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database import AsyncSessionLocal
from app.domain.models.models import User, Stock, Watchlist
from app.core.security import hash_password
from sqlalchemy import select

async def seed():
    async with AsyncSessionLocal() as session:
        # 1. Buat Dummy User
        result = await session.execute(select(User).where(User.email == "admin@example.com"))
        user = result.scalar_one_or_none()
        
        if not user:
            print("Creating dummy user...")
            user = User(
                email="admin@example.com",
                password_hash=hash_password("admin123"),
                full_name="Admin AI Stock",
                subscription_tier="premium"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print("User created: admin@example.com / admin123")
        else:
            print("User already exists! (admin@example.com / admin123)")
            
        # 2. Buat Dummy Stocks
        stocks_data = [
            {"ticker": "BBCA.JK", "company_name": "Bank Central Asia Tbk", "sector": "Finance", "exchange": "IDX"},
            {"ticker": "GOTO.JK", "company_name": "GoTo Gojek Tokopedia Tbk", "sector": "Technology", "exchange": "IDX"},
            {"ticker": "TLKM.JK", "company_name": "Telkom Indonesia (Persero) Tbk", "sector": "Infrastructure", "exchange": "IDX"},
            {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "exchange": "NASDAQ"},
            {"ticker": "MSFT", "company_name": "Microsoft Corp.", "sector": "Technology", "exchange": "NASDAQ"},
        ]
        
        for stock_data in stocks_data:
            result = await session.execute(select(Stock).where(Stock.ticker == stock_data["ticker"]))
            if not result.scalar_one_or_none():
                stock = Stock(**stock_data)
                session.add(stock)
                
        await session.commit()
        print("Stocks seeded.")
        
        # 3. Buat Dummy Watchlist
        result = await session.execute(select(Watchlist).where(Watchlist.user_id == user.id, Watchlist.stock_ticker == "BBCA.JK"))
        if not result.scalar_one_or_none():
            watchlist = Watchlist(user_id=user.id, stock_ticker="BBCA.JK", notes="Saham pantauan utama")
            session.add(watchlist)
            await session.commit()
            print("Watchlist seeded.")
            
        print("Seeding database selesai!")

if __name__ == "__main__":
    asyncio.run(seed())
