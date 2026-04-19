Build minimal backend (Flask). Single POST /scan endpoint that increments a counter and returns current count.

## Required Function of Backend

backend has five functions it should provide endpoints to, there are other functions we can add but those are the MVPs:

1. Activate a session — **(targeted: CR dashboard)** — (Create new one)
    
2. Deactivate a session — **(targeted: CR dashboard)** — (Close an already running one)
    
3. Send a scan — **(targeted: ESP32)**
    
4. Retrieve a single room count — **(targeted: ESP32)**
    
5. Retrieve data needed for dashboard, which is the following for each room (room name, current count for the active session, total capacity) — **(targeted: CR dashboard)**
    

Notice no (Create Room or Delete Room or Update Room) rooms are specified and can't be created nor destroyed for now.

## Data Models

The for our system are

1. `emergency_session`
    
    1. `id` (PK)
        
    2. `started_at`
        
    3. `ended_at` (null means still running)
        
2. `room`
    
    1. `id` (PK)
        
    2. `name`
        
    3. `total_capacity`
        
3. `employee`
    
    1. `id` (PK)
        
    2. `card_id`
        
4. `scan`
    
    1. `id` (PK)
        
    2. `room_id` (FK -> `room`)
        
    3. `session_id` (FK -> `emergency_session`)
        
    4. `card_id` (FK -> `employee.card_id`)
        
    5. `scanned_at`
        

## API Endpoints

- `POST /api/emergency-sessions`: Create new session if no active session exist. sets `id` and `started_at`.
    
    - **Body**: None
        
    - **Response**: return created session info as shown + `201` status code
        
        ```
        {
            "ended_at": null,
            "id": "5d7902b6-3d3c-44db-8366-76954feca345",
            "started_at": "2026-04-13T14:27:06.571689+00:00"
        }
        ```
        
    - **Errors handled**
        
        - Case 1: Client try to create new session while there already exist an active -> endpoint return error message and `400` status code
            
            ```
            {
                "error": "An active session already exist with id:
                          5d7902b6-3d3c-44db-8366-76954feca345"
            }
            ```
            

---

- `PATCH /api/emergency-sessions/active`: Deactivate the only active session (since there is only one active session, there is no need for passing id). Automatically sets `ended_at`.
    
    - **Body**: None
        
    - **Response**: return deactivated session info after `ended_at` setting + `200` status code.
        
        ```
        {
            "ended_at": "2026-04-13T14:37:26.897910+00:00",
            "id": "e97a2eee-deba-41c8-9263-e3b62f6867dd",
            "started_at": "2026-04-13T14:37:24.663476+00:00"
        }
        ```
        
    - **Errors handled**
        
        - Case 1: Client try to deactivate active session, while no active sessions exist -> endpoint return error message and `400` status code
            
            ```
            {
                "error": "No active session exist"
            }
            ```
            

---

- `POST /api/scan`: Create a scan using passed info.
    
    - **Body**
        
        ```
        {
          "card_id": 1,
          "room_id": 2
        }
        ```
        
    - **Response**: return created scan info + 201 status code
        
        ```
        {
          "id": 456, 
          "card_id": 1,
          "room_id": 2,
          "session_id": 4
        }
        ```
        
    - **Edge Cases**: Employee scanned for other room in the same active session -> Update `room_id` in the same scan to be the last entered room. and since we compute headcount from `scans` dictionary then no problem arises. return the newly updated scan info + `200` status code.
        
        ```
        {
          "card_id": "C1",
          "id": "e38d7b0c-4de3-466a-8d35-90d2f3542cef",
          "room_id": "R2",
          "scanned_at": "2026-04-13T14:50:41.835447+00:00",
          "session_id": "feed3b96-f812-44ab-ab1b-39c6953cefdb"
        }
        ```
        
    - **Errors Handled**
        
        - No active session -> return error response + `400` status code
            
            ```
            {
              "error": "No active session exist"
            }
            ```
            
        - Missing field in request body -> return error response + `400` status code
            
            ```
            {
              "error": "request missing some fields"
            }
            ```
            
        - Passed room id doesn't exist -> return error response + `400` status code
            
            ```
            {
              "error": "No room with id: R1" 
            }
            ```
            
        - Passed card id doesn't exist -> return error response + `400` status code
            
            ```
            {
              "error": "No card with id: C1"
            }
            ```
            
        - Employee scanned twice for same room in the same active session -> return error response + `400` status code
            
            ```
            {
              "error": "Employee with card with id: C1
                        already scanned for room with id: R1"
            }
            ```
            

---

- `GET /api/rooms/<room_id>`
    
    - **Body**: None
        
    - **Response:** Return specific room info + current count (computed from `scans` dictionary)
        
        ```
        {
          "id" : "R1",
          "name" : "Room 1",
          "current_headcount": 60,
          "total_capacity": 100
        }
        ```
        
    - Errors Handled: No room with passed id -> return error message + `400` status code
        
        ```
        {
          "error": "No room with id: R5"
        }
        ```
        

---

- `GET /api/rooms`
    
    - **Body**: None
        
    - **Response**: Return same as `GET /api/rooms/<int:id>` but for all rooms
        
        ```
        {
          "id" : "R1",
          "name" : "Room 1",
          "current_headcount": 60,
          "total_capacity": 100
        }
        ```
        
Those are endpoints in the same order as the functions needed from the backend either from the ESP32 or the dashboard.

## Running the Backend

### Prerequisites
- Python 3.x
- [uv](https://docs.astral.sh/uv/) package manager

### Setup
Clone the repository and install dependencies:
```bash
git clone git@github.com:AbdullahKhkmba/omnisafe-flask-backend.git
cd omnisafe-flask-backend
uv sync
```

### Running
```bash
uv run python app.py
```

Server will start at `http://127.0.0.1:5001`