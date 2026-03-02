# AImedic.tech13.ca — Full Working Django Project (Patients / Doctors / Drug Marts / Super Admin)

This is a ready-to-deploy Django project with:
- Separate login pages for each role
- Separate dashboards (patient/doctor/pharmacy/super admin)
- Appointment requests (Visit/Phone) + approvals
- Refill requests + doctor approval + send instruction to drug mart + pharmacy status updates
- In-app notifications
- Dummy/demo data seeder (creates accounts + sample requests)

## 1) Install
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Database + Dummy data
```bash
python manage.py migrate
python manage.py seed_demo
```

## 3) Run
```bash
python manage.py runserver 0.0.0.0:8000
```

## URLs
- Landing (choose portal): `/`
- Patient login:  `/login/user/`
- Doctor login:   `/login/doctor/`
- Drug mart login:`/login/pharmacy/`
- Super admin:    `/login/super/`
- Django admin:   `/admin/`

## Demo credentials
- Super Admin: `superadmin` / `Admin@12345`
- Doctor: `doctor1` / `Doctor@12345`
- Drug Mart: `pharmacy1` / `Pharma@12345`
- Patients: `patient1` / `Patient@12345`, `patient2` / `Patient@12345`

## Production (Nginx + SSL)
Set environment vars (recommended):
- `DJANGO_ALLOWED_HOSTS=aimedic.tech13.ca`
- `DJANGO_CSRF_TRUSTED=https://aimedic.tech13.ca`
- `DJANGO_SECRET_KEY=<your-secret>`
- `DJANGO_DEBUG=0`

Then run gunicorn behind nginx.
