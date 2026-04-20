from flask import Flask, jsonify, request
from datetime import datetime, timezone
import uuid
import state

app = Flask(__name__)

def headcount(room_id):
    headcount = 0
    for scan in state.scans.values():
        if scan['room_id'] == room_id and scan['session_id'] == state.active_session_id:
            headcount += 1

    return headcount

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

@app.route('/api/emergency-sessions/active', methods=['PATCH'])
def deactivate():
    if state.active_session_id is not None:
        session_id = state.active_session_id
        session = state.sessions[session_id]        # Active session info
        session["ended_at"] = datetime.now(timezone.utc).isoformat()    # deactivated
        state.active_session_id = None
        return jsonify(session), 200   
    else:
        return jsonify({"error": "No active session exist"}), 400     

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
    response_list = []

    for room in state.rooms.values():
        room_info = {
            'id': room['id'],
            'name': room['name'],
            'current_headcount': headcount(room['id']),
            'total_capacity': room['total_capacity']
        }

        response_list.append(room_info)

    return jsonify(response_list), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
