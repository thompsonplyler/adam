from app import create_app, socketio

app = create_app()
 
if __name__ == '__main__':
    # Use SocketIO server to enable websockets in dev
    socketio.run(app, debug=True)