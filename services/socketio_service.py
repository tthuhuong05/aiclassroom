"""
Socket.IO service for real-time study room communication
"""
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import session
import logging
import uuid
from collections import defaultdict

logger = logging.getLogger(__name__)

# Initialize SocketIO (will be initialized in app.py)
socketio = None
room_messages = defaultdict(dict)

def init_socketio(app):
    """Initialize SocketIO with the Flask app"""
    global socketio
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
    register_handlers()
    return socketio

def get_socketio():
    """Get the SocketIO instance"""
    return socketio

def register_handlers():
    """Register Socket.IO event handlers"""
    if not socketio:
        return
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        user_id = session.get("user", {}).get("id")
        username = session.get("username")
        if user_id:
            logger.info(f"User {username} ({user_id}) connected")
            emit('connected', {'user_id': user_id, 'username': username})
        else:
            logger.warning("Anonymous user tried to connect")
            return False

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        user_id = session.get("user", {}).get("id")
        username = session.get("username")
        logger.info(f"User {username} ({user_id}) disconnected")

    @socketio.on('room:join')
    def handle_join_room(data):
        """Handle user joining a study room"""
        from model.study_room_model import StudyRoomModel
        
        room_id = data.get('room_id')
        user_id = data.get('user_id') or session.get("user", {}).get("id")
        username = data.get('username') or session.get("username", "Guest")
        
        if not user_id or not room_id:
            emit('room:error', {'message': 'Invalid request'})
            return
        
        try:
            model = StudyRoomModel()
            room = model.get_room_by_id(int(room_id))
            
            if not room:
                emit('room:error', {'message': 'Room not found'})
                return
            
            # Check if room is full
            member_count = room.get('member_count', 0) or 0
            max_members = room.get('max_members', 10) or 10
            
            if member_count >= max_members:
                emit('room:error', {'message': 'Room is full'})
                return
            
            # Join the Socket.IO room
            join_room(str(room_id))
            
            # Get room info
            room_info = {
                'room_id': room_id,
                'name': room.get('name'),
                'topic': room.get('topic'),
                'language': room.get('language'),
                'level': room.get('level'),
                'description': room.get('description'),
                'max_members': max_members,
                'member_count': member_count
            }
            
            emit('room:info', room_info)
            
            # Get current participants
            members = model.get_room_members(int(room_id))
            participants = [{
                'user_id': m.get('user_id'), 
                'username': m.get('username'), 
                'role': m.get('role'),
                'avatar_path': m.get('avatar_path')  # Thêm avatar_path
            } for m in members]
            
            emit('room:participants', {'participants': participants})
            
            # Notify others
            socketio.emit('room:user-joined', {
                'user_id': user_id,
                'username': username
            }, room=str(room_id), include_self=False)
            
            logger.info(f"User {username} joined room {room_id}")
            
        except Exception as e:
            logger.error(f"Error joining room: {e}")
            emit('room:error', {'message': 'Failed to join room'})

    @socketio.on('room:leave')
    def handle_leave_room(data):
        """Handle user leaving a study room"""
        room_id = data.get('room_id')
        user_id = session.get("user", {}).get("id")
        username = session.get("username", "Guest")
        
        if room_id:
            leave_room(str(room_id))
            socketio.emit('room:user-left', {
                'user_id': user_id,
                'username': username
            }, room=str(room_id), include_self=False)
            logger.info(f"User {username} left room {room_id}")

    @socketio.on('chat:message')
    def handle_chat_message(data):
        """Handle chat message"""
        room_id = data.get('room_id')
        message = data.get('message', '').strip()
        user_id = data.get('user_id') or session.get("user", {}).get("id")
        username = data.get('username') or session.get("username", "Guest")
        # Ưu tiên avatar_path từ data, sau đó từ session
        avatar_path = data.get('avatar_path') or data.get('avatar') or session.get("user", {}).get("avatar_path")
        reply_to = data.get('reply_to')
        
        if not message or not room_id or not user_id:
            return
        
        message_id = data.get('message_id') or str(uuid.uuid4())
        role = None
        try:
            from model.study_room_model import StudyRoomModel
            model = StudyRoomModel()
            role = model.get_member_role(int(room_id), int(user_id)) or 'member'
        except Exception as exc:
            logger.warning(f"Could not determine member role: {exc}")
            role = 'member'
        
        payload = {
            'message_id': message_id,
            'user_id': user_id,
            'username': username,
            'avatar': avatar_path,
            'avatar_path': avatar_path,  # Thêm avatar_path để frontend xử lý
            'role': role,
            'message': message[:1000],
            'reply_to': reply_to,
            'timestamp': int(__import__('time').time() * 1000),
            'edited': False,
            'deleted': False
        }
        room_key = str(room_id)
        room_messages[room_key][message_id] = payload
        
        # Cập nhật last_activity_at
        try:
            import datetime
            from model.study_room_model import StudyRoomModel
            model = StudyRoomModel()
            with model._connect() as conn:
                cursor = conn.cursor()
                now = datetime.datetime.now().isoformat()
                cursor.execute("""
                    UPDATE study_rooms SET last_activity_at = ? WHERE id = ?
                """, (now, int(room_id)))
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to update last_activity_at: {e}")
        
        socketio.emit('chat:message', payload, room=room_key)

    @socketio.on('chat:edit')
    def handle_chat_edit(data):
        """Handle editing a message"""
        room_id = data.get('room_id')
        message_id = data.get('message_id')
        new_text = (data.get('message') or '').strip()
        user_id = data.get('user_id') or session.get("user", {}).get("id")

        if not room_id or not message_id or not new_text or not user_id:
            return

        room_key = str(room_id)
        message = room_messages[room_key].get(message_id)
        if not message:
            emit('chat:error', {'message': 'Không tìm thấy tin nhắn'})
            return

        is_owner = session.get("role") == "teacher" or session.get("user", {}).get("is_admin")
        if message.get('user_id') != user_id and not is_owner:
            emit('chat:error', {'message': 'Không có quyền chỉnh sửa'})
            return

        message['message'] = new_text[:1000]
        message['edited'] = True
        message['timestamp_edit'] = int(__import__('time').time() * 1000)
        socketio.emit('chat:edit', message, room=room_key)

    @socketio.on('chat:delete')
    def handle_chat_delete(data):
        """Handle deleting a message"""
        room_id = data.get('room_id')
        message_id = data.get('message_id')
        user_id = data.get('user_id') or session.get("user", {}).get("id")

        if not room_id or not message_id or not user_id:
            return

        room_key = str(room_id)
        message = room_messages[room_key].get(message_id)
        is_owner = session.get("role") == "teacher" or session.get("user", {}).get("is_admin")
        if not message or (message.get('user_id') != user_id and message.get('role') != 'admin' and not is_owner):
            return

        message['deleted'] = True
        socketio.emit('chat:delete', {'message_id': message_id, 'room_id': room_key}, room=room_key)

    @socketio.on('webrtc:offer')
    def handle_webrtc_offer(data):
        """Handle WebRTC offer"""
        target_id = data.get('target_id')
        offer = data.get('offer')
        user_id = session.get("user", {}).get("id")
        
        if target_id and offer:
            socketio.emit('webrtc:offer', {
                'from': user_id,
                'offer': offer
            }, room=target_id, include_self=False)

    @socketio.on('webrtc:answer')
    def handle_webrtc_answer(data):
        """Handle WebRTC answer"""
        target_id = data.get('target_id')
        answer = data.get('answer')
        user_id = session.get("user", {}).get("id")
        
        if target_id and answer:
            socketio.emit('webrtc:answer', {
                'from': user_id,
                'answer': answer
            }, room=target_id, include_self=False)

    @socketio.on('webrtc:ice-candidate')
    def handle_webrtc_ice(data):
        """Handle WebRTC ICE candidate"""
        target_id = data.get('target_id')
        candidate = data.get('candidate')
        user_id = session.get("user", {}).get("id")
        
        if target_id and candidate:
            socketio.emit('webrtc:ice-candidate', {
                'from': user_id,
                'candidate': candidate
            }, room=target_id, include_self=False)

    @socketio.on('room:screen-share-start')
    def handle_screen_share_start(data):
        """Handle screen share start"""
        room_id = data.get('room_id')
        user_id = data.get('user_id') or session.get("user", {}).get("id")
        username = data.get('username') or session.get("username", "Guest")
        
        if room_id and user_id:
            socketio.emit('room:screen-share-start', {
                'user_id': user_id,
                'username': username
            }, room=str(room_id), include_self=False)
            logger.info(f"User {username} started screen sharing in room {room_id}")

    @socketio.on('room:screen-share-stop')
    def handle_screen_share_stop(data):
        """Handle screen share stop"""
        room_id = data.get('room_id')
        user_id = data.get('user_id') or session.get("user", {}).get("id")
        
        if room_id and user_id:
            socketio.emit('room:screen-share-stop', {
                'user_id': user_id
            }, room=str(room_id), include_self=False)
            logger.info(f"User {user_id} stopped screen sharing in room {room_id}")

    @socketio.on('room:mute-user')
    def handle_mute_user(data):
        """Handle mute user request from admin"""
        from model.study_room_model import StudyRoomModel
        
        room_id = data.get('room_id')
        admin_id = session.get("user", {}).get("id")
        target_user_id = data.get('target_user_id')
        username = data.get('username', 'Guest')
        
        if not room_id or not admin_id or not target_user_id:
            emit('room:error', {'message': 'Invalid request'})
            return
        
        try:
            model = StudyRoomModel()
            # Kiểm tra quyền admin
            admin_role = model.get_member_role(int(room_id), int(admin_id))
            if admin_role != 'admin':
                emit('room:error', {'message': 'Bạn không có quyền thực hiện hành động này'})
                return
            
            # Gửi thông báo mute đến user bị mute
            socketio.emit('room:user-muted', {
                'muted_by': admin_id,
                'message': f'Bạn đã bị tắt tiếng bởi quản trị viên'
            }, room=str(target_user_id))
            
            # Thông báo cho tất cả trong phòng
            socketio.emit('room:user-muted-notification', {
                'target_user_id': target_user_id,
                'username': username,
                'muted_by': admin_id
            }, room=str(room_id), include_self=False)
            
            logger.info(f"Admin {admin_id} muted user {target_user_id} in room {room_id}")
        except Exception as e:
            logger.error(f"Error muting user: {e}")
            emit('room:error', {'message': 'Không thể tắt tiếng người dùng'})

    @socketio.on('room:unmute-user')
    def handle_unmute_user(data):
        """Handle unmute user request from admin"""
        from model.study_room_model import StudyRoomModel
        
        room_id = data.get('room_id')
        admin_id = session.get("user", {}).get("id")
        target_user_id = data.get('target_user_id')
        username = data.get('username', 'Guest')
        
        if not room_id or not admin_id or not target_user_id:
            emit('room:error', {'message': 'Invalid request'})
            return
        
        try:
            model = StudyRoomModel()
            # Kiểm tra quyền admin
            admin_role = model.get_member_role(int(room_id), int(admin_id))
            if admin_role != 'admin':
                emit('room:error', {'message': 'Bạn không có quyền thực hiện hành động này'})
                return
            
            # Gửi thông báo unmute đến user
            socketio.emit('room:user-unmuted', {
                'unmuted_by': admin_id,
                'message': f'Bạn đã được bật lại tiếng bởi quản trị viên'
            }, room=str(target_user_id))
            
            # Thông báo cho tất cả trong phòng
            socketio.emit('room:user-unmuted-notification', {
                'target_user_id': target_user_id,
                'username': username,
                'unmuted_by': admin_id
            }, room=str(room_id), include_self=False)
            
            logger.info(f"Admin {admin_id} unmuted user {target_user_id} in room {room_id}")
        except Exception as e:
            logger.error(f"Error unmuting user: {e}")
            emit('room:error', {'message': 'Không thể bật lại tiếng người dùng'})

    @socketio.on('room:kick-user')
    def handle_kick_user(data):
        """Handle kick user request from admin"""
        from model.study_room_model import StudyRoomModel
        
        room_id = data.get('room_id')
        admin_id = session.get("user", {}).get("id")
        target_user_id = data.get('target_user_id')
        username = data.get('username', 'Guest')
        
        if not room_id or not admin_id or not target_user_id:
            emit('room:error', {'message': 'Invalid request'})
            return
        
        try:
            model = StudyRoomModel()
            # Kiểm tra quyền admin
            admin_role = model.get_member_role(int(room_id), int(admin_id))
            if admin_role != 'admin':
                emit('room:error', {'message': 'Bạn không có quyền thực hiện hành động này'})
                return
            
            # Xóa user khỏi phòng
            # Lưu ý: leave_room không cho phép admin rời, nhưng kick thì được
            # Cần thêm method riêng hoặc sửa logic
            with model._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM study_room_members 
                    WHERE room_id = ? AND user_id = ?
                """, (int(room_id), int(target_user_id)))
                conn.commit()
            
            # Gửi thông báo kick đến user bị kick
            socketio.emit('room:user-kicked', {
                'room_id': room_id,
                'message': 'Bạn đã bị kick khỏi phòng bởi quản trị viên'
            }, room=str(target_user_id))
            
            # Thông báo cho tất cả trong phòng
            socketio.emit('room:user-kicked-notification', {
                'target_user_id': target_user_id,
                'username': username,
                'kicked_by': admin_id
            }, room=str(room_id), include_self=False)
            
            # Cập nhật danh sách participants
            members = model.get_room_members(int(room_id))
            participants = [{
                'user_id': m.get('user_id'), 
                'username': m.get('username'), 
                'role': m.get('role'),
                'avatar_path': m.get('avatar_path')
            } for m in members]
            socketio.emit('room:participants', {'participants': participants}, room=str(room_id))
            
            logger.info(f"Admin {admin_id} kicked user {target_user_id} from room {room_id}")
        except Exception as e:
            logger.error(f"Error kicking user: {e}")
            emit('room:error', {'message': 'Không thể kick người dùng'})
