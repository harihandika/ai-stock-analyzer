import asyncio
import os
import sys

# Tambahkan path agar bisa mengimpor module dari app/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database import AsyncSessionLocal
from app.domain.models.models import User
from app.core.security import hash_password
from sqlalchemy import select

async def reset_password():
    async with AsyncSessionLocal() as session:
        # Cari user berdasarkan email
        result = await session.execute(select(User).where(User.email == "harisnowpop@gmail.com"))
        user = result.scalar_one_or_none()
        
        if user:
            print(f"[*] Menemukan akun: {user.email}")
            # Timpa password lamanya dengan hash yang baru dari sistem FastAPI
            user.password_hash = hash_password("admin123")
            
            # Wajib dicommit agar tersimpan di database
            session.add(user)
            await session.commit()
            print("[✓] SUKSES! Password berhasil direset menjadi: admin123")
        else:
            print("[x] GAGAL: Akun harisnowpop@gmail.com tidak ditemukan di database.")

if __name__ == "__main__":
    asyncio.run(reset_password())
