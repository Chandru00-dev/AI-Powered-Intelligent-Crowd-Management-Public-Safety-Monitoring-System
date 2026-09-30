# AI-Powered Intelligent Crowd Management and Public Safety Monitoring System

A modular, enterprise-grade CCTV surveillance and crowd analytics platform engineered for public safety, density tracking, and incident monitoring.

---

## 1. Project Overview

The AI-Powered Intelligent Crowd Management and Public Safety Monitoring System is a real-time computer vision and surveillance platform designed to monitor pedestrian movement, detect hazardous density levels, assess bottleneck congestion, and detect physical safety risks across public venues (transit terminals, stadiums, pedestrian plazas, and campus facilities).

The current implementation comprises:
- **Phase 1: Project Foundation** - Authentication, database persistence, role authorization, responsive command center dashboard, and telemetry visualization.
- **Phase 2: Camera and Video Input Subsystem** - Unified video ingestion engine supporting pre-recorded video files, USB/laptop webcams, and RTSP CCTV camera feeds with non-blocking OpenCV streaming.
- **Phase 3: YOLO Person Detection and Tracking** - Real-time Ultralytics YOLOv8 pedestrian inference, ByteTrack multi-object persistent tracking, trajectory motion trails, and automated crowd headcount telemetry.
- **Phase 4: Zone Configuration and Crowd Density** - 4-zone spatial quadrant partitioning, foot-point ground plane mapping, density classification (LOW, MEDIUM, HIGH, CRITICAL), color-mapped Gaussian density heatmaps, and real-time zone telemetry.
- **Phase 5: Congestion Detection and Bottleneck Analytics** - Real-time pedestrian dwell time tracking, stationary crowd clustering, spatial bottleneck detection, continuous 0-100% congestion indexing, and in-memory alert dispatching.

---

## 2. System Architecture

```
[ CCTV Camera / Webcam / Video File ]
                  |
                  v
          [ OpenCV Engine ]
  (DirectShow / FFMPEG / Looping File Reader)
                  |
                  v
       [ VideoSource Subsystem ]
  (Decoupled Thread-safe Ingestion Pipeline)
                  |
                  v
       [ FastAPI Application ]
  (Auth / CRUD / Non-blocking MJPEG Streaming)
                  |
                  +--------------------------------+
                  |                                |
                  v                                v
       [ PostgreSQL Database ]        [ HTML5 / CSS3 / Vanilla JS ]
   (SQLAlchemy / Auto Fallback)       (Dashboard / Live Monitoring)
```

---

## 3. Technology Stack

### Frontend
- HTML5 (Semantic document markup)
- CSS3 (Vanilla CSS with custom design tokens, glassmorphism, responsive grid layout)
- Vanilla JavaScript (ES6 Modules, Fetch API client)
- Chart.js (Crowd density and headcount trends visualization)
- Font Awesome (Vector icons via CDN)

### Backend
- Python 3.10+
- FastAPI (High-performance asynchronous REST API framework)
- Pydantic v2 (Input validation and serialization)
- SQLAlchemy 2.0 (ORM and schema migrations)
- PostgreSQL (Primary enterprise relational database)
- SQLite (Automated zero-configuration fallback for local development)
- PyJWT & Bcrypt (Cryptographic token issuance and password hashing)

### Video and Computer Vision Engine
- OpenCV (cv2) - Multi-threaded frame capture, DirectShow driver integration, FFMPEG RTSP stream ingestion, and MJPEG encoding.
- NumPy - Numerical array manipulation.

---

## 4. Directory Structure

```
c:/programming/Final year project/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   |-- __init__.py          # API router registry
|   |   |   |-- auth.py              # Authentication endpoints (/login, /me, /register)
|   |   |   |-- cameras.py           # Camera management & streaming endpoints
|   |   |   |-- dashboard.py         # Summary analytics and KPI counters
|   |   |   |-- settings.py          # Safety threshold management
|   |   |   |-- system.py            # System health and diagnostic endpoints
|   |   |-- core/
|   |   |   |-- config.py            # Environment configuration loader
|   |   |   |-- database.py          # SQLAlchemy engine & session manager
|   |   |   |-- init_app.py          # Database seeder & sample video generator
|   |   |   |-- security.py          # Bcrypt hashing & JWT token generator
|   |   |-- models/
|   |   |   |-- __init__.py          # Model exports
|   |   |   |-- base.py              # Base timestamp mixin
|   |   |   |-- user.py              # User & UserRole models
|   |   |   |-- camera.py            # Camera model
|   |   |   |-- setting.py           # SystemSetting model
|   |   |   |-- events.py            # Alert, DetectionEvent, CrowdMetric models
|   |   |-- schemas/
|   |   |   |-- __init__.py          # Schema exports
|   |   |   |-- user.py              # User request & response schemas
|   |   |   |-- camera.py            # Camera CRUD schemas
|   |   |   |-- setting.py           # System calibration schemas
|   |   |   |-- dashboard.py         # Dashboard summary schemas
|   |   |-- services/
|   |   |   |-- auth_service.py      # Dependency injection for user auth & roles
|   |   |   |-- camera_service.py    # Camera management & MJPEG frame generator
|   |   |   |-- video_source.py      # Abstract VideoSource, VideoFile, Webcam, RTSP
|   |   |-- main.py                  # Application entry point & static file mount
|   |-- ai/                          # Scaffolded directories for Phase 3+
|   |   |-- detection/
|   |   |-- tracking/
|   |   |-- crowd/
|   |   |-- congestion/
|   |   |-- fire_smoke/
|   |   |-- suspicious_objects/
|   |   |-- abandoned_objects/
|   |   |-- alert_engine/
|   |-- tests/
|   |   |-- conftest.py              # Pytest fixture & database setup
|   |   |-- test_auth.py             # Authentication & JWT test suite
|   |   |-- test_cameras.py          # Camera CRUD & validation test suite
|   |   |-- test_video_source.py     # Video source & OpenCV test suite
|   |-- init_postgres_db.py          # Interactive PostgreSQL setup helper
|   |-- requirements.txt             # Backend dependencies
|   |-- .env                         # Active configuration
|   |-- .env.example                 # Template configuration
|-- frontend/
|   |-- index.html                   # Automatic session routing
|   |-- login.html                   # Authentication portal
|   |-- dashboard.html               # Main command center interface
|   |-- cameras.html                 # Camera management interface
|   |-- live-monitoring.html         # Live surveillance player console
|   |-- settings.html                # Safety thresholds configuration
|   |-- css/
|   |   |-- global.css               # Core styling tokens & components
|   |   |-- login.css                # Login specific styles
|   |   |-- dashboard.css            # Command center styles
|   |   |-- cameras.css              # Camera & stream console styles
|   |   |-- responsive.css           # Mobile & tablet media queries
|   |-- js/
|   |   |-- api.js                   # Centralized Fetch wrapper with JWT injection
|   |   |-- auth.js                  # Session & role state controller
|   |   |-- dashboard.js             # Dashboard controller & Chart.js renderer
|   |   |-- cameras.js               # Camera registration & test controller
|   |   |-- live-monitoring.js       # Live player controller & stream manager
|   |   |-- settings.js              # System threshold controller
|   |   |-- utils.js                 # Toast notifications & formatting utilities
|   |-- assets/
|       |-- icons/                   # SVG fallback assets
|       |-- samples/
|           |-- sample_crowd.mp4     # Auto-synthesized crowd CCTV demo video
|-- models/
|   |-- pretrained/                  # Designated directory for YOLO weights
|   |-- custom/                      # Designated directory for custom models
|-- training/                        # Training scripts & fine-tuning pipelines
|-- README.md                        # Documentation
```

---

## 5. Database Schema

The database architecture is designed with strict relational integrity, primary keys, foreign keys, and indexes:

### 1. `users`
- `id` (INTEGER, Primary Key, Auto-increment)
- `email` (VARCHAR 255, Unique, Indexed)
- `username` (VARCHAR 100, Unique, Indexed)
- `full_name` (VARCHAR 255)
- `hashed_password` (VARCHAR 255)
- `role` (ENUM: `ADMIN`, `SECURITY_OPERATOR`)
- `is_active` (BOOLEAN)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### 2. `cameras`
- `id` (INTEGER, Primary Key, Auto-increment)
- `name` (VARCHAR 150, Indexed)
- `location` (VARCHAR 200)
- `input_type` (ENUM: `VIDEO_FILE`, `WEBCAM`, `RTSP`)
- `source` (TEXT)
- `username` (VARCHAR 100, Nullable)
- `password_encrypted` (VARCHAR 255, Nullable, Hidden from client)
- `status` (ENUM: `ONLINE`, `OFFLINE`, `CONNECTING`, `ERROR`, `DISABLED`)
- `enabled` (BOOLEAN)
- `resolution` (VARCHAR 50)
- `fps` (FLOAT)
- `description` (TEXT)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### 3. `system_settings`
- `id` (INTEGER, Primary Key, Auto-increment)
- `key` (VARCHAR 100, Unique, Indexed)
- `value` (TEXT)
- `description` (TEXT)
- `category` (VARCHAR 50)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### 4. `alerts`
- `id` (INTEGER, Primary Key, Auto-increment)
- `camera_id` (INTEGER, Foreign Key to `cameras.id`)
- `alert_type` (ENUM: `HIGH_CROWD`, `CONGESTION`, `FIRE`, `SMOKE`, `SUSPICIOUS_OBJECT`, `ABANDONED_OBJECT`, `CAMERA_OFFLINE`, `SYSTEM_ERROR`)
- `severity` (ENUM: `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `message` (TEXT)
- `confidence` (FLOAT)
- `status` (ENUM: `ACTIVE`, `REVIEWED`, `RESOLVED`)
- `reviewed_by` (VARCHAR 100)
- `resolution_notes` (TEXT)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### 5. `detection_events`
- `id` (INTEGER, Primary Key, Auto-increment)
- `camera_id` (INTEGER, Foreign Key to `cameras.id`)
- `event_type` (VARCHAR 50, Indexed)
- `details` (TEXT)
- `confidence` (FLOAT)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### 6. `crowd_metrics` & `zone_metrics`
- Prepared relational structures for Phase 3 and Phase 4 spatial density and zone counting logs.

---

## 6. API Endpoints

### System & Diagnostics
- `GET /api/system/health` - Check database status, uptime, and host operating system.

### Authentication & Authorization
- `POST /api/auth/login` - Validate credentials and receive JWT bearer token.
- `GET /api/auth/me` - Fetch profile of currently authenticated user.
- `POST /api/auth/register` - Create new operator or administrator account (Admin only).

### Camera Management
- `GET /api/cameras` - List all registered surveillance cameras (credentials masked).
- `POST /api/cameras` - Register a new camera node (supports probe testing).
- `GET /api/cameras/{id}` - Retrieve detailed camera configuration.
- `PUT /api/cameras/{id}` - Update camera settings (Admin only).
- `DELETE /api/cameras/{id}` - Remove camera and release background capture resources (Admin only).
- `POST /api/cameras/{id}/test` - Probe existing camera connection and return resolution/latency.
- `POST /api/cameras/test-raw` - Test arbitrary camera endpoint prior to persisting in registry.
- `POST /api/cameras/{id}/enable` - Enable camera feed.
- `POST /api/cameras/{id}/disable` - Disable camera feed and release pipeline.
- `GET /api/cameras/{id}/stream` - Real-time non-blocking MJPEG live video stream (supports `annotate=true/false` and `heatmap=true/false`).
- `GET /api/cameras/{id}/metrics` - Real-time Phase 3 AI tracking metrics (headcount, peak, speed, active track list).
- `GET /api/cameras/{id}/zones` - Real-time Phase 4 zone spatial telemetry (Zone A, B, C, D headcount, density, occupancy ratio).
- `PUT /api/cameras/{id}/zones` - Configure zone capacities for a camera node (Admin only).
- `GET /api/cameras/{id}/congestion` - Real-time Phase 5 congestion analytics (congestion index, level, stationary count, cluster details, active alert).

### Dashboard & Analytics
- `GET /api/dashboard/summary` - Aggregate metrics (Total/Online cameras, current crowd, active alerts, trend data).

### Settings & Calibration
- `GET /api/settings` - Retrieve crowd, congestion, and safety thresholds.
- `PUT /api/settings` - Update threshold limits (Admin only).

---

## 7. Installation and Setup

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13 installed
- PostgreSQL 14+ installed (Optional for first run; SQLite zero-config fallback is built-in)
- Web browser (Chrome, Edge, Firefox)

### Step 1: Clone or Navigate to Directory
```powershell
cd "c:\programming\Final year project"
```

### Step 2: Install Python Dependencies
```powershell
pip install -r backend/requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env` (already done by default):
```powershell
cp backend/.env.example backend/.env
```

---

## 8. Setting Up PostgreSQL

PostgreSQL is the designated enterprise storage engine. The application contains automatic connectivity verification: if PostgreSQL credentials are not yet supplied, it smoothly operates using SQLite so that you can evaluate the project immediately.

### Option A: Automatic Setup using PostgreSQL Helper Script
Run the included configuration utility:
```powershell
python backend/init_postgres_db.py
```
This utility:
1. Prompts for your PostgreSQL superuser password.
2. Creates the target database `crowd_safety_db` if it does not already exist.
3. Automatically updates `DATABASE_URL` in `backend/.env`.

### Option B: Manual Setup via psql
If you prefer running commands manually:
```sql
CREATE DATABASE crowd_safety_db;
```
Then update `backend/.env`:
```env
DATABASE_URL="postgresql://postgres:your_password@localhost:5432/crowd_safety_db"
```

When you start the backend, SQLAlchemy will automatically detect PostgreSQL and create all required tables.

---

## 9. Running the Application

### Starting the Backend Server
Run the FastAPI application from the project root:
```powershell
python backend/app/main.py
```
The server will start at:
- Application & UI: `http://localhost:8000`
- Interactive API Documentation (Swagger): `http://localhost:8000/docs`
- Alternative Documentation (ReDoc): `http://localhost:8000/redoc`

### Accessing the Frontend
The frontend files are served directly by FastAPI. Simply open:
```
http://localhost:8000
```
Or open `frontend/index.html` via any static HTTP web server (such as VS Code Live Server on port 5500).

---

## 10. Default Login Credentials

The system seeds two standard accounts upon initial startup:

### System Administrator
- **Email:** `admin@crowdsafety.ai`
- **Password:** `Admin@12345`
- **Privileges:** Full camera management, threshold configuration, user creation, live monitoring.

### Security Operator
- **Email:** `operator@crowdsafety.ai`
- **Password:** `Operator@12345`
- **Privileges:** Live surveillance monitoring, viewing dashboard telemetry, inspecting camera status.

---

## 11. Camera Testing and Input Verification

### A. Testing Pre-Recorded Video File
1. Log in to `http://localhost:8000`.
2. Go to **Camera Management** (`cameras.html`).
3. Click **Register New Camera Node**.
4. Select Video Feed Source Type: **Pre-recorded Video File (.mp4)**.
5. Click **Use Packaged Sample Video** (auto-fills `frontend/assets/samples/sample_crowd.mp4`).
6. Click **Test Connection** to verify frame reading and resolution.
7. Click **Save Node**.
8. Go to **Live Monitoring** (`live-monitoring.html`) to observe continuous looped playback.

### B. Testing USB / Laptop Webcam
1. Open **Register New Camera Node**.
2. Select Source Type: **USB / Integrated Laptop Webcam**.
3. In **Video Source Endpoint**, enter `0` (or `1` if an external USB webcam is connected).
4. Click **Test Connection**. The webcam will activate briefly via OpenCV DirectShow, report resolution and frame rate.
5. Click **Save Node** and navigate to Live Monitoring to view the real-time webcam feed.

### C. Testing RTSP CCTV Camera
1. Open **Register New Camera Node**.
2. Select Source Type: **RTSP CCTV IP Camera Stream**.
3. In **Video Source Endpoint**, enter the full RTSP URL:
   ```
   rtsp://192.168.1.100:554/live/ch0
   ```
   Or provide username and password in the dedicated security fields.
4. Click **Test Connection**.
   - If reachable: Reports stream verification, resolution, and latency.
   - If unreachable: Displays a helpful diagnostic message (checking network routing, credentials, or stream path) without revealing passwords or crashing the server.

---

## 12. Verification and Automated Test Results

The backend contains a comprehensive test suite covering authentication, camera lifecycle, video source engines, YOLO person detection, ByteTrack tracking, spatial zone partitioning, density classification, Gaussian heatmaps, dwell time tracking, stationary clustering, congestion indexing, and in-memory alert dispatching.

Run the test suite:
```powershell
python -m pytest backend/tests/ -v
```

Test coverage includes 33 passing tests across 6 test suites:
- `test_system_health`: System health check endpoint.
- `test_login_success`: JWT credential generation and role validation.
- `test_login_invalid_password`: 401 Unauthorized handling for incorrect passwords.
- `test_get_me_authenticated`: Protected route verification using bearer token.
- `test_get_me_unauthorized`: Rejection of unauthenticated requests.
- `test_list_cameras`: Camera registry listing with masked credentials.
- `test_create_and_manage_camera`: Camera creation, probe test, disable, enable, and deletion.
- `test_invalid_rtsp_connection_handling`: Graceful handling of offline RTSP streams.
- `test_yolo_detector_initialization`: YOLOv8 model initialization from weights.
- `test_yolo_detection_on_frame`: Person detection bounding box extraction.
- `test_bytetrack_tracking`: ByteTrack persistent tracking, unique IDs, and velocity calculation.
- `test_frame_annotation`: Visual HUD overlay and bounding box corner rendering.
- `test_crowd_counter_db_persistence`: Database logging of crowd metrics.
- `test_ai_pipeline_end_to_end`: Unified pipeline integration with live video frames.
- `test_zone_config_containment`: Spatial bounding box point containment logic.
- `test_density_analyzer_classification`: Density level classification (LOW, MEDIUM, HIGH, CRITICAL).
- `test_density_analyzer_quadrant_mapping`: Foot-point mapping of pedestrians into quadrant zones.
- `test_density_analyzer_heatmap_generation`: Gaussian density heatmap generation with color mapping.
- `test_density_analyzer_db_persistence`: Periodic database persistence to zone_metrics table.
- `test_frame_annotation_with_zones`: Frame annotation rendering quadrant crosshairs and zone badges.
- `test_get_camera_zones_endpoint`: Verification of GET /api/cameras/{id}/zones endpoint.
- `test_update_camera_zones_endpoint`: Verification of PUT /api/cameras/{id}/zones configuration endpoint.
- `test_dashboard_summary_zones`: Verification of dashboard summary zone breakdown telemetry.
- `test_pedestrian_state_tracking`: Individual pedestrian dwell time and stationary state tracking.
- `test_congestion_analyzer_normal_flow`: Congestion analysis on normal pedestrian movement flow.
- `test_congestion_analyzer_stationary_clustering`: Spatial proximity clustering and bottleneck zone mapping.
- `test_congestion_alert_triggering`: In-memory congestion alert dispatch on sustained congestion.
- `test_annotator_with_congestion`: Stream annotation with congestion cluster halos and stationary tags.
- `test_get_camera_congestion_endpoint`: Verification of GET /api/cameras/{id}/congestion endpoint.
- `test_dashboard_summary_includes_congestion_level`: Verification of dashboard congestion telemetry.
- `test_video_file_source`: Video file connection, frame reading, resolution metadata, and continuous looping.
- `test_nonexistent_video_file_handling`: Non-crashing error handling for missing video files.
- `test_generate_status_frame`: OpenCV HUD graphic generation for offline cameras.

---

## 13. Current Capabilities (Phase 1, 2, 3, 4 & 5)

- Real-time YOLOv8 person detection running on all video streams.
- ByteTrack persistent tracking assigning individual IDs to pedestrians.
- Real-time bounding box annotations with corner brackets and motion trails.
- Live HUD displaying headcount, peak crowd, tracker algorithm, frame rate, congestion index, and bottleneck locations.
- 4-Zone spatial quadrant partitioning (Zone A: Main Entrance, Zone B: Concourse Plaza, Zone C: Escalator Corridor, Zone D: South Exit Gate).
- Ground-plane foot-point projection mapping pedestrians accurately into physical zones.
- Automated density classification based on occupancy capacity ratios (LOW, MEDIUM, HIGH, CRITICAL).
- Color-mapped Gaussian density heatmap generation overlay for visualization of crowd concentration spots.
- Individual pedestrian dwell time and stagnation tracking with stationary badges (`STOPPED 12s`).
- Spatial proximity clustering detecting stationary pedestrian groupings and bottleneck formations.
- Continuous Congestion Index calculation (0% to 100%) classified into NORMAL, MODERATE, CONGESTED, and SEVERE.
- Transient in-memory alert dispatching when congestion thresholds are exceeded.
- Interactive Live Monitoring Console and Command Center Dashboard with real-time congestion telemetry bars and bottleneck callouts.

---

## 14. Next Phase

**Phase 6 — Fire and Smoke Hazard Detection**
- Computer vision color, motion, and texture analysis for flame and smoke recognition.
- Specialized spatial hazard boundary detection.
- Emergency alert dispatching and evacuation zone warnings.



