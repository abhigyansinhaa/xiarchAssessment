import datetime
from backend.models.database import engine, Base, SessionLocal, Employee, LeaveRequest, init_db


def seed_database():
    init_db()
    db = SessionLocal()

    # If already seeded, skip
    if db.query(Employee).count() > 0:
        print("[seed_db] Database already contains records. Skipping seed.")
        db.close()
        return

    print("[seed_db] Seeding HR Central Database...")

    # Seed Employees
    employees_data = [
        # Leadership & HR
        {
            "id": 100,
            "name": "Rajesh Singhania",
            "email": "rajesh.singhania@xiarch.in",
            "department": "Executive",
            "role": "Chief Executive Officer",
            "hire_date": datetime.date(2018, 1, 15),
            "manager_id": None,
            "manager_name": None,
            "total_annual_leave": 30,
            "used_annual_leave": 5,
            "sick_leave_balance": 12,
            "casual_leave_balance": 8,
            "location": "New Delhi"
        },
        {
            "id": 104,
            "name": "Priya Iyer",
            "email": "priya.iyer@xiarch.in",
            "department": "Human Resources",
            "role": "Head of People Operations",
            "hire_date": datetime.date(2020, 3, 1),
            "manager_id": 100,
            "manager_name": "Rajesh Singhania",
            "total_annual_leave": 24,
            "used_annual_leave": 6,
            "sick_leave_balance": 10,
            "casual_leave_balance": 7,
            "location": "Bengaluru"
        },
        # Engineering Management & Engineers
        {
            "id": 101,
            "name": "Aarav Sharma",
            "email": "aarav.sharma@xiarch.in",
            "department": "Engineering",
            "role": "Engineering VP",
            "hire_date": datetime.date(2019, 2, 10),
            "manager_id": 100,
            "manager_name": "Rajesh Singhania",
            "total_annual_leave": 24,
            "used_annual_leave": 8,
            "sick_leave_balance": 12,
            "casual_leave_balance": 6,
            "location": "Bengaluru"
        },
        {
            "id": 102,
            "name": "Diya Patel",
            "email": "diya.patel@xiarch.in",
            "department": "Engineering",
            "role": "Senior Backend Engineer",
            "hire_date": datetime.date(2021, 6, 15),
            "manager_id": 101,
            "manager_name": "Aarav Sharma",
            "total_annual_leave": 24,
            "used_annual_leave": 15,
            "sick_leave_balance": 9,
            "casual_leave_balance": 4,
            "location": "Bengaluru"
        },
        {
            "id": 105,
            "name": "Amit Patel",
            "email": "amit.patel@xiarch.in",
            "department": "Engineering",
            "role": "Principal AI Architect",
            "hire_date": datetime.date(2019, 3, 15),  # >7 years tenure! Eligible for sabbatical
            "manager_id": 101,
            "manager_name": "Aarav Sharma",
            "total_annual_leave": 24,
            "used_annual_leave": 9,
            "sick_leave_balance": 12,
            "casual_leave_balance": 7,
            "location": "Bengaluru"
        },
        {
            "id": 111,
            "name": "Rohan Gupta",
            "email": "rohan.gupta@xiarch.in",
            "department": "Engineering",
            "role": "Full Stack Engineer",
            "hire_date": datetime.date(2022, 8, 1),
            "manager_id": 101,
            "manager_name": "Aarav Sharma",
            "total_annual_leave": 24,
            "used_annual_leave": 4,
            "sick_leave_balance": 12,
            "casual_leave_balance": 8,
            "location": "Bengaluru"
        },
        {
            "id": 112,
            "name": "Meera Nambiar",
            "email": "meera.nambiar@xiarch.in",
            "department": "Engineering",
            "role": "DevOps & Cloud Engineer",
            "hire_date": datetime.date(2023, 1, 10),
            "manager_id": 101,
            "manager_name": "Aarav Sharma",
            "total_annual_leave": 24,
            "used_annual_leave": 10,
            "sick_leave_balance": 11,
            "casual_leave_balance": 5,
            "location": "Bengaluru"
        },
        {
            "id": 113,
            "name": "Vikram Sethi",
            "email": "vikram.sethi@xiarch.in",
            "department": "Engineering",
            "role": "Cybersecurity Analyst",
            "hire_date": datetime.date(2022, 11, 20),
            "manager_id": 101,
            "manager_name": "Aarav Sharma",
            "total_annual_leave": 24,
            "used_annual_leave": 12,
            "sick_leave_balance": 8,
            "casual_leave_balance": 6,
            "location": "New Delhi"
        },
        # Product & Design
        {
            "id": 103,
            "name": "Rohan Verma",
            "email": "rohan.verma@xiarch.in",
            "department": "Product",
            "role": "VP of Product",
            "hire_date": datetime.date(2020, 5, 12),
            "manager_id": 100,
            "manager_name": "Rajesh Singhania",
            "total_annual_leave": 24,
            "used_annual_leave": 7,
            "sick_leave_balance": 12,
            "casual_leave_balance": 5,
            "location": "Mumbai"
        },
        {
            "id": 108,
            "name": "Ananya Roy",
            "email": "ananya.roy@xiarch.in",
            "department": "Design",
            "role": "Lead Product Designer",
            "hire_date": datetime.date(2021, 9, 1),
            "manager_id": 103,
            "manager_name": "Rohan Verma",
            "total_annual_leave": 24,
            "used_annual_leave": 11,
            "sick_leave_balance": 10,
            "casual_leave_balance": 6,
            "location": "Bengaluru"
        },
        {
            "id": 114,
            "name": "Kavita Reddy",
            "email": "kavita.reddy@xiarch.in",
            "department": "Product",
            "role": "Senior Product Manager",
            "hire_date": datetime.date(2023, 4, 15),
            "manager_id": 103,
            "manager_name": "Rohan Verma",
            "total_annual_leave": 24,
            "used_annual_leave": 6,
            "sick_leave_balance": 12,
            "casual_leave_balance": 8,
            "location": "Hyderabad"
        },
        # Marketing & Growth
        {
            "id": 106,
            "name": "Neha Gupta",
            "email": "neha.gupta@xiarch.in",
            "department": "Marketing",
            "role": "Marketing Director",
            "hire_date": datetime.date(2022, 2, 1),
            "manager_id": 100,
            "manager_name": "Rajesh Singhania",
            "total_annual_leave": 24,
            "used_annual_leave": 9,  # Has 15 remaining annual leaves
            "sick_leave_balance": 11,
            "casual_leave_balance": 7,
            "location": "Mumbai"
        },
        {
            "id": 115,
            "name": "Tanvi Joshi",
            "email": "tanvi.joshi@xiarch.in",
            "department": "Marketing",
            "role": "Content & Growth Specialist",
            "hire_date": datetime.date(2023, 7, 10),
            "manager_id": 106,
            "manager_name": "Neha Gupta",
            "total_annual_leave": 24,
            "used_annual_leave": 5,
            "sick_leave_balance": 12,
            "casual_leave_balance": 8,
            "location": "Mumbai"
        },
        {
            "id": 116,
            "name": "Sameer Khan",
            "email": "sameer.khan@xiarch.in",
            "department": "Marketing",
            "role": "SEO & Performance Marketer",
            "hire_date": datetime.date(2024, 2, 1),
            "manager_id": 106,
            "manager_name": "Neha Gupta",
            "total_annual_leave": 24,
            "used_annual_leave": 3,
            "sick_leave_balance": 12,
            "casual_leave_balance": 8,
            "location": "Bengaluru"
        },
        # Finance & Legal
        {
            "id": 107,
            "name": "Vikram Singh",
            "email": "vikram.singh@xiarch.in",
            "department": "Finance",
            "role": "Finance Controller",
            "hire_date": datetime.date(2020, 10, 1),
            "manager_id": 100,
            "manager_name": "Rajesh Singhania",
            "total_annual_leave": 24,
            "used_annual_leave": 8,
            "sick_leave_balance": 12,
            "casual_leave_balance": 6,
            "location": "New Delhi"
        },
        {
            "id": 117,
            "name": "Pooja Hegde",
            "email": "pooja.hegde@xiarch.in",
            "department": "Finance",
            "role": "Senior Accountant",
            "hire_date": datetime.date(2022, 5, 20),
            "manager_id": 107,
            "manager_name": "Vikram Singh",
            "total_annual_leave": 24,
            "used_annual_leave": 14,
            "sick_leave_balance": 10,
            "casual_leave_balance": 4,
            "location": "Bengaluru"
        },
        # Operations & Customer Success
        {
            "id": 109,
            "name": "Karan Malhotra",
            "email": "karan.malhotra@xiarch.in",
            "department": "Operations",
            "role": "Director of Operations",
            "hire_date": datetime.date(2021, 3, 1),
            "manager_id": 100,
            "manager_name": "Rajesh Singhania",
            "total_annual_leave": 24,
            "used_annual_leave": 10,
            "sick_leave_balance": 12,
            "casual_leave_balance": 7,
            "location": "Bengaluru"
        },
        {
            "id": 110,
            "name": "Sneha Kulkarni",
            "email": "sneha.kulkarni@xiarch.in",
            "department": "Customer Success",
            "role": "Customer Success Lead",
            "hire_date": datetime.date(2022, 9, 15),
            "manager_id": 109,
            "manager_name": "Karan Malhotra",
            "total_annual_leave": 24,
            "used_annual_leave": 12,
            "sick_leave_balance": 9,
            "casual_leave_balance": 5,
            "location": "Pune"
        },
        {
            "id": 118,
            "name": "Rahul Deshmukh",
            "email": "rahul.deshmukh@xiarch.in",
            "department": "Customer Success",
            "role": "Technical Support Specialist",
            "hire_date": datetime.date(2023, 6, 1),
            "manager_id": 110,
            "manager_name": "Sneha Kulkarni",
            "total_annual_leave": 24,
            "used_annual_leave": 7,
            "sick_leave_balance": 12,
            "casual_leave_balance": 8,
            "location": "Pune"
        },
        {
            "id": 119,
            "name": "Priya Sharma",
            "email": "priya.sharma@xiarch.in",
            "department": "Engineering",
            "role": "Senior Frontend Engineer",
            "hire_date": datetime.date(2021, 10, 1),
            "manager_id": 101,
            "manager_name": "Aarav Sharma",
            "total_annual_leave": 24,
            "used_annual_leave": 11,
            "sick_leave_balance": 10,
            "casual_leave_balance": 6,
            "location": "Bengaluru"
        }
    ]

    for emp in employees_data:
        db.add(Employee(**emp))

    db.commit()

    # Seed Sample Leave Requests
    leaves_data = [
        {
            "employee_id": 102,
            "employee_name": "Diya Patel",
            "leave_type": "Medical",
            "start_date": datetime.date(2026, 9, 2),
            "end_date": datetime.date(2026, 9, 5),
            "days_requested": 4,
            "reason": "Severe viral fever and flu",
            "status": "APPROVED",
            "approver_notes": "Approved by Aarav Sharma. Medical certificate attached."
        },
        {
            "employee_id": 104,
            "employee_name": "Priya Iyer",
            "leave_type": "Casual",
            "start_date": datetime.date(2026, 9, 3),
            "end_date": datetime.date(2026, 9, 3),
            "days_requested": 1,
            "reason": "Personal family event",
            "status": "APPROVED",
            "approver_notes": "Self approved as HR head."
        },
        {
            "employee_id": 115,
            "employee_name": "Tanvi Joshi",
            "leave_type": "Annual",
            "start_date": datetime.date(2026, 10, 5),
            "end_date": datetime.date(2026, 10, 9),
            "days_requested": 5,
            "reason": "Attending sibling wedding in Jaipur",
            "status": "PENDING",
            "approver_notes": None
        },
        {
            "employee_id": 116,
            "employee_name": "Sameer Khan",
            "leave_type": "Annual",
            "start_date": datetime.date(2026, 10, 12),
            "end_date": datetime.date(2026, 10, 16),
            "days_requested": 5,
            "reason": "Family vacation",
            "status": "PENDING",
            "approver_notes": None
        },
        {
            "employee_id": 111,
            "employee_name": "Rohan Gupta",
            "leave_type": "Casual",
            "start_date": datetime.date(2026, 9, 28),
            "end_date": datetime.date(2026, 9, 29),
            "days_requested": 2,
            "reason": "Home relocation",
            "status": "PENDING",
            "approver_notes": None
        }
    ]

    for lv in leaves_data:
        db.add(LeaveRequest(**lv))

    db.commit()
    print(f"[seed_db] Successfully seeded {len(employees_data)} employees and {len(leaves_data)} leave requests.")
    db.close()


if __name__ == "__main__":
    seed_database()
