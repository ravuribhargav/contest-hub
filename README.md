# Contest Management System
## RVR & JC College of Engineering — Department of CSE (Data Science)

A premium institutional platform for managing hackathons, coding contests, and workshops.

---

## Setup & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Apply database migrations
python manage.py migrate

# 3. Seed sample data (admin + students + contests)
python manage.py seed_data

# 4. Start the development server
python manage.py runserver
```

Open: **http://127.0.0.1:8000**

---

## Login Credentials

| Role    | Username | Password     |
|---------|----------|-------------|
| Admin   | admin    | admin123    |
| Student | alice    | student123  |
| Student | bob      | student123  |
| Student | carol    | student123  |

---

## Key URLs

| URL                          | Description            |
|------------------------------|------------------------|
| `/`                          | Homepage               |
| `/contests/`                 | Browse contests        |
| `/contests/<id>/`            | Contest detail         |
| `/archive/`                  | Completed contests     |
| `/teams/`                    | My Teams               |
| `/registrations/`            | My Registrations       |
| `/accounts/login/`           | Login page             |
| `/accounts/profile/`         | Student profile        |
| `/admin/`                    | Admin panel            |
| `/admin/contests/`           | Manage contests        |
| `/admin/users/`              | Manage users           |
| `/admin/announcements/`      | Manage announcements   |

---

## Features

- Contest management (Hackathon, Coding Contest, Workshop)
- Team system with invite codes
- Eligibility enforcement (branch + year)
- Live countdown timer to next contest
- Admin participant export (CSV)
- Announcement bar management
- Contest archive grouped by year
- Premium website-style UI (Inter font, clean cards)

---

© 2026 RVR & JC College of Engineering. Developed by CSE (Data Science).
