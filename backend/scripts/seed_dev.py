"""种子 demo student（幂等）。"""
import asyncio

from sqlalchemy import select

from selflearn.domain.student import Student
from selflearn.infra.db import SessionLocal


async def main() -> None:
    async with SessionLocal() as s:
        existing = (
            await s.execute(select(Student).where(Student.display_name == "demo-student"))
        ).scalar_one_or_none()
        if existing:
            print(f"[seed] demo-student already exists: {existing.student_id}")
            return
        stu = Student(display_name="demo-student")
        s.add(stu)
        await s.commit()
        print(f"[seed] inserted demo-student: {stu.student_id}")


if __name__ == "__main__":
    asyncio.run(main())
