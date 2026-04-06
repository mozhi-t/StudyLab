from __future__ import annotations

SERVER_CONFIG_TEMPLATE = {
    "server_name": "StudyLab Exam Server",
    "max_clients": 30,
    "auth_mode": 0,
    "listen_port": 8765,
}

ACCOUNTS_TEMPLATE = {
    "accounts": [
        {
            "username": "student1",
            "password": "123456",
            "display_name": "学生1",
        }
    ]
}

CONNECTION_TEMPLATE = {
    "connections": []
}
