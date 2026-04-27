from flask import Flask, jsonify, request
from datetime import datetime, timezone
import uuid
import state
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 

def headcount(room_id, session_id=None):
    if session_id is None:
        session_id = state.active_session_id
    
    headcount = 0
    for scan in state.scans.values():
        if scan['room_id'] == room_id and scan['session_id'] == session_id:
            headcount += 1

    return headcount

# return last scan time or None if room was not compeleted
def completed_at(room_id, session_id):
    room = state.rooms[room_id]
    complete_time = None

    if headcount(room_id, session_id) == room['total_capacity']:
        # find time of last scan
        for scan in state.scans.values():
            if scan['room_id'] == room_id and scan['session_id'] == session_id:
                if complete_time is None:
                    complete_time = scan['scanned_at']
                else:
                    complete_time = max(complete_time, scan['scanned_at'])
    
    return complete_time

@app.route('/api/emergency-sessions', methods=['GET'])
def get_sessions():
    sessions_list =[]

    for session in state.sessions.values():
        if session['ended_at'] is None:    # skip active sessions
            continue   
        
        rooms_list = []
        for room in state.rooms.values():
            room_info = {
                'id': room['id'],
                'name': room['name'],
                'final_headcount': headcount(room['id'], session['id']),
                'total_capacity': room['total_capacity'],
                'completed_at': completed_at(room['id'], session['id'])
            }

            rooms_list.append(room_info)
        
        sessions_list.append({
            "session_id": session['id'],
            "started_at": session['started_at'],
            "ended_at": session['ended_at'],
            "rooms": rooms_list
        })

    # Sort by ended_at timestamp in descending order (most recent first)
    sessions_list.sort(key=lambda s: s['ended_at'], reverse=True)
    
    return jsonify(sessions_list), 200

@app.route('/api/emergency-sessions', methods=['POST'])
def activate():
    if state.active_session_id is None:
        active_session_id = str(uuid.uuid4())
        active_session = {
                'id': active_session_id,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'ended_at': None
            }
        
        state.sessions[active_session_id] = active_session
        state.active_session_id = active_session_id
        return jsonify(active_session), 201
    
    else:
        return jsonify({"error": 
            "An active session already exist with id: " + state.active_session_id}), 400

@app.route('/api/emergency-sessions/active', methods=['GET'])
def get_active_session():
    if state.active_session_id is None:
        return jsonify({"error": "No active session"}), 404
    return jsonify(state.sessions[state.active_session_id]), 200

@app.route('/api/emergency-sessions/active', methods=['PATCH'])
def deactivate():
    if state.active_session_id is not None:
        session = state.sessions[state.active_session_id]
        session["ended_at"] = datetime.now(timezone.utc).isoformat()
        state.active_session_id = None
        return jsonify(session), 200
    else:
        return jsonify({"error": "No active session exists"}), 400

@app.route('/api/scan', methods=['POST'])
def scan():
    scan_data = request.get_json(force=True)
    room_id = scan_data.get('room_id')
    card_id = scan_data.get('card_id')

    if state.active_session_id is None:
        return jsonify({
            "error_code": "NO_ACTIVE_SESSION",
            "error": "No active emergency session"
        }), 409  # Conflict — request is valid but state doesn't allow it

    if room_id is None or card_id is None:
        return jsonify({
            "error_code": "MISSING_FIELDS",
            "error": "Request missing room_id or card_id"
        }), 422  # Unprocessable Entity — structure is wrong

    if room_id not in state.rooms:
        return jsonify({
            "error_code": "ROOM_NOT_FOUND",
            "error": f"No room with id: {room_id}"
        }), 404  # Not Found — resource doesn't exist

    if card_id not in state.cards:
        return jsonify({
            "error_code": "CARD_NOT_FOUND",
            "error": f"No card with id: {card_id}"
        }), 404  # Not Found

    for scan in state.scans.values():
        if scan['card_id'] == card_id and scan['room_id'] == room_id and scan['session_id'] == state.active_session_id:
            return jsonify({
                "error_code": "ALREADY_SCANNED",
                "error": f"Card {card_id} already scanned for room {room_id}"
            }), 409  # Conflict — duplicate

    for scan in state.scans.values():
        if scan['card_id'] == card_id and scan['session_id'] == state.active_session_id:
            scan['room_id'] = room_id
            return jsonify({
                "error_code": "ROOM_TRANSFERRED",
                **scan
            }), 200

    scan_id = str(uuid.uuid4())
    scan = {
        'id': scan_id,
        'room_id': room_id,
        'session_id': state.active_session_id,
        'card_id': card_id,
        'card_holder': state.cards[card_id],
        'scanned_at': datetime.now(timezone.utc).isoformat()
    }
    state.scans[scan_id] = scan
    return jsonify(scan), 201

@app.route('/api/rooms/<room_id>', methods=['GET'])
def get_room_by_id(room_id):
    if room_id not in state.rooms:
        return jsonify({
                "error": "No room with id: " + room_id
            }), 400
    
    room = state.rooms[room_id]

    response = {
        'id': room['id'],
        'name': room['name'],
        'current_headcount': headcount(room['id']),
        'total_capacity': room['total_capacity']
    }
    
    return jsonify(response), 200

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    rooms_list = []
    asid = state.active_session_id
    for room in state.rooms.values():
        room_info = {
            'id': room['id'],
            'name': room['name'],
            'current_headcount': headcount(room['id']),
            'total_capacity': room['total_capacity'],
            'completed_at': completed_at(room['id'], asid)
        }

        rooms_list.append(room_info)

    if(asid is not None):
        response = {
            "session_active": True,
            "started_at": state.sessions[asid]['started_at'],
            "rooms": rooms_list
        }
    else:
        response = {
            "session_active": False,
            "started_at": None,
            "rooms": rooms_list
        }
    

    return jsonify(response), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
