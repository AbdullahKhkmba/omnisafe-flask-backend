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
        return jsonify({"success": "session deactivated successfully", "session_info": session}), 200   
    else:
        return jsonify({"error": "No active session exist"}), 400     

@app.route('/api/scan', methods=['POST'])
def scan():
    scan_data = request.get_json()
    room_id = scan_data.get('room_id')
    card_id = scan_data.get('card_id')

    if state.active_session_id is None:
        return jsonify({
            "error": "No active session exist"
        }), 400
    
    if room_id is None or card_id is None:
        return jsonify({
                "error": "request missing some fields"
            }), 400
    
    if room_id not in state.rooms:
        return jsonify({
                "error": "No room with id: " + room_id
            }), 400
    
    if card_id not in state.cards:
        return jsonify({
                "error": "No card with id: " + card_id
            }), 400
    
    # TODO: if employee scan twice for same room and in same session edge case
    for scan in state.scans.values():
        if scan['card_id'] == card_id and scan['room_id'] == room_id and scan['session_id'] == state.active_session_id:
            return jsonify({
                    "error": "Employee with card with id: " + card_id + " already scanned for room with id: " + room_id
                }), 400

    # TODO: if employee scan on another room in same session edge case
    for scan in state.scans.values():
        if scan['card_id'] == card_id and scan['session_id'] == state.active_session_id:
            scan['room_id'] = room_id
            return jsonify(scan), 200 

    scan_id = str(uuid.uuid4())
    scan = {
        'id': scan_id,
        'room_id': room_id,
        'session_id': state.active_session_id,
        'card_id': card_id,
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
    app.run(debug=True, host="127.0.0.1", port=5001)
