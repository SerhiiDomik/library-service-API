# Library Service API

DRF API for managing book borrowings with notifications

## Features

- JWT authentication
- Admin panel
- API documentation via Swagger
- Book inventory management
- Borrowing system
- User management
- Telegram notifications for:
  - New borrowings
  - Overdue returns (via Celery periodic tasks)
- Redis + Celery for background tasks
- Filtering for books and borrowings

## Quick Start with Docker

### 1. Clone the Repository

Clone the repository to your local machine:

```bash
git clone https://github.com/your-repository.git
cd your-repository
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit .env file with your credentials
- Django secret key
- Database credentials
- TELEGRAM_BOT_TOKEN (get from @BotFather)
- TELEGRAM_CHAT_ID (your admin chat ID)

### 3. Start services

Docker should be installed
```bash
docker-compose up --build
```

### 4. Initialize database

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### 5. Set up periodic tasks
1. Access admin panel: http://localhost:8000/admin/
2. Navigate to Periodic tasks
3. Create new task:
- Name: Check overdue borrowings
- Task: borrowings.tasks.check_overdue_borrowings
- Schedule: Daily at 9:00 AM

## Access

- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/
- Docs: http://localhost:8000/api/doc/swagger/
