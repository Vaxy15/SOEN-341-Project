# SOEN-341 Project

Project for **SOEN 341 – Software Process** at Concordia University.

---
### Students:

| Name                       | ID       | GitHub Handle    |
|----------------------------|----------|------------------|
| Mountaga Sy                | 40312584 | @mountagv7       |
| Adam Othmani               | 40287816 | @64NG            |
| Souméya Diop               | 40197160 | @soumeyadiop     |
| Abderrahmane Bensassi-Nour | 40317017 | @Abderrahmane102 |
| Anthony Vaccaro            | 40214876 | @Vaxy15          |
| Anthony Mastromonaco       | 40077240 | @Anthony-Mastro  |
| Mahdi Rahman               | 40282926 | @MahdiRahman4    |

   
# 🎓 Campus Events & Ticketing Web Application

## 🔧 Environment Setup

### 1. Clone the repository
```bash
git clone <repository-url>
cd SOEN-341-Project-1
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Copy the example environment file and configure your settings:
```bash
cp env.example .env
```

Edit `.env` file with your settings:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

### 5. Database Setup
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Run Development Server
```bash
python manage.py runserver
```

## Description
A web platform designed to help students **discover, organize, and attend events on campus**.  
The system enables students to browse upcoming events, claim digital tickets, and check in via QR codes.  
Organizers can create and manage events, track attendance, and export attendee data, while administrators oversee moderation and analytics.  


---

## Objectives
- Build a **central hub** for students to explore and attend campus events.
- Provide organizers with tools to **create, promote, and manage** events efficiently.
- Give administrators oversight through **moderation and analytics dashboards**.
- Encourage **student engagement** and simplify ticketing with digital QR-based check-ins.

---

## Core Features

### Student Event Experience
- **Event Discovery**  
  - Browse and search events with filters (date, category, organization).  
- **Event Management**  
  - Save events to a personal calendar.  
  - Claim free or mock-paid tickets.  
  - Receive a **digital ticket with a unique QR code**.  

### Organizer Event Management
- **Event Creation**  
  - Add event details: title, description, date/time, location, ticket capacity, and type (free or paid).  
- **Event Analytics**  
  - Per-event dashboard: tickets issued, attendance rates, remaining capacity.  
- **Tools**  
  - Export attendee lists to CSV.  
  - Integrated **QR scanner** for ticket validation (via upload or camera).  

### Administrator Dashboard & Moderation
- **Platform Oversight**  
  - Approve organizer accounts.  
  - Moderate event listings for policy compliance.  
- **Analytics**  
  - View global stats: number of events, tickets issued, participation trends.  
- **Management**  
  - Manage organizations and assign roles.  

### Additional Feature (to be proposed)
Alongside the core features, one additional feature will be designed in consultation with the TA. Examples include:
- **Waitlists** for sold-out events.  
- **Calendar sync** with Google/Apple Calendar.  

---

## Tech Stack (planned)
- **Backend:** Python (Django + Django REST Framework / FastAPI)  
- **Frontend:** React  
- **Database:** PostgreSQL  
- **Authentication:** Django Auth 
- **QR Codes:** Python `qrcode` library + browser QR scanner  
- **Deployment:** Docker, Gunicorn, Nginx, PostgreSQL, S3 for storage  


---

## ⚙️ Setting Up for Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/SOEN-341-Project.git
   cd SOEN-341-Project
   ```

2. **Create and activate a virtual environment**  
   Windows (PowerShell): 
   ```bash
   py -m venv venv
   venv\Scripts\Activate.ps1
   ```
   If you get a script execution error:
   ```bash 
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   venv\Scripts\Activate.ps1
   ```
   macOS/Linux:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   If requirements.txt does not exist yet:
   ```bash
   pip install django django-filter pillow qrcode
   pip freeze > requirements.txt
   ```
4. **Apply database migrations**   
   ```bash
   python manage.py migrate
   ```
5. **Create a superuser (admin account for django)**
   ```bash
   python manage.py createsuperuser
   ```
6. **Run the development server**
   ```bash
   Run the development server
   ```
   Open your browser:  
   Home page --> [http://127.0.0.1:8000/](http://127.0.0.1:8000/)  
   Admin loging page --> [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)